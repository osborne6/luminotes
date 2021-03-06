import cherrypy

from Expose import expose
from Expire import strongly_expire
from Validate import validate, Valid_int, Valid_string, Valid_bool
from Notebooks import Notebooks
from Users import Users, grab_user_id
from Groups import Groups
from Files import Files
from Forums import Forums, Forum
from Database import Valid_id, end_transaction
from Users import update_auth
from model.Note import Note
from model.Notebook import Notebook
from model.User import User
from view.Main_page import Main_page
from view.Front_page import Front_page
from view.Tour_page import Tour_page
from view.Upgrade_page import Upgrade_page
from view.Download_page import Download_page
from view.Forums_page import Forums_page
from view.Notebook_rss import Notebook_rss
from view.Json import Json
from view.Error_page import Error_page
from view.Not_found_page import Not_found_page
from view.Close_page import Close_page


class Root( object ):
  """
  The root of the controller hierarchy, corresponding to the "/" URL.
  """
  def __init__( self, database, settings, suppress_exceptions = False ):
    """
    Create a new Root object with the given settings.

    @type database: controller.Database
    @param database: database to use for all controllers
    @type settings: dict
    @param settings: CherryPy-style settings 
    @rtype: Root
    @return: newly constructed Root
    """
    self.__database = database
    self.__settings = settings
    self.__users = Users(
      database,
      settings[u"luminotes.http_url"],
      settings[u"luminotes.https_url"],
      settings[u"luminotes.support_email"],
      settings[u"luminotes.payment_email"],
      settings[u"luminotes.rate_plans"],
      settings[u"luminotes.download_products"],
    )
    self.__groups = Groups( database, self.__users )
    self.__files = Files(
      database,
      self.__users,
      settings[u"luminotes.download_products"],
      settings[u"luminotes.web_server"],
    )
    self.__notebooks = Notebooks( database, self.__users, self.__files, settings[ u"luminotes.https_url"] )
    self.__forums = Forums( database, self.__notebooks, self.__users )
    self.__blog = Forum( database, self.__notebooks, self.__users, u"blog" )
    self.__suppress_exceptions = suppress_exceptions # used for unit tests

  @expose( Main_page )
  @end_transaction
  @grab_user_id
  @validate(
    note_title = unicode,
    invite_id = Valid_id( none_okay = True ),
    after_login = Valid_string( min = 0, max = 1000 ),
    plan = Valid_int( none_okay = True ),
    yearly = Valid_bool( none_okay = True ),
    user_id = Valid_id( none_okay = True ),
  )
  def default( self, note_title, invite_id = None, after_login = None, plan = None, yearly = False, user_id = None ):
    """
    Convenience method for accessing a note in the main notebook by name rather than by note id.

    @type note_title: unicode
    @param note_title: title of the note to return
    @type invite_id: unicode
    @param invite_id: id of the invite used to get to this note (optional)
    @type after_login: unicode
    @param after_login: URL to redirect to after login (optional, must start with "/")
    @type plan: int
    @param plan: rate plan index (optional, defaults to None)
    @type yearly: bool
    @param yearly: True for yearly plan, False for monthly (optional, defaults to False)
    @rtype: unicode
    @return: rendered HTML page
    """
    # if the user is logged in and not using https, and they request the sign up or login note, then
    # redirect to the https version of the page (if available)
    https_url = self.__settings[u"luminotes.https_url"]
    https_proxy_ip = self.__settings[u"luminotes.https_proxy_ip"]
    
    if note_title in ( u"sign_up", u"login" ) and https_url and cherrypy.request.remote_addr != https_proxy_ip:
      if invite_id:
        return dict( redirect = u"%s/%s?invite_id=%s" % ( https_url, note_title, invite_id ) )
      if after_login:
        return dict( redirect = u"%s/%s?after_login=%s" % ( https_url, note_title, after_login ) )
      if plan:
        return dict( redirect = u"%s/%s?plan=%s&yearly=%s" % ( https_url, note_title, plan, yearly ) )
      else:
        return dict( redirect = u"%s/%s" % ( https_url, note_title ) )

    anonymous = self.__database.select_one( User, User.sql_load_by_username( u"anonymous" ) )
    if anonymous:
      main_notebook = self.__database.select_one( Notebook, anonymous.sql_load_notebooks( undeleted_only = True ) )

    result = self.__users.current( user_id = user_id )

    note_title = note_title.replace( u"_", " " )
    note = self.__database.select_one( Note, main_notebook.sql_load_note_by_title( note_title ) )
    if not note:
      raise cherrypy.NotFound

    result.update( self.__notebooks.contents( main_notebook.object_id, user_id = user_id, note_id = note.object_id ) )
    if invite_id:
      result[ "invite_id" ] = invite_id
    if after_login and after_login.startswith( u"/" ):
      result[ "after_login" ] = after_login
    if plan:
      result[ "signup_plan" ] = plan
      result[ "signup_yearly" ] = yearly

    return result

  @expose()
  def r( self, password_reset_id ):
    """
    Redirect to the password reset URL, based on the given password_reset id. The sole purpose of
    this method is to shorten password reset URLs sent by email so email clients don't wrap them.
    """
    # if the value looks like an id, it's a password reset id, so redirect
    try:
      validator = Valid_id()
      password_reset_id = validator( password_reset_id )
    except ValueError:
      raise cherrypy.NotFound

    return dict(
      redirect = u"/users/redeem_reset/%s" % password_reset_id,
    )

  @expose()
  def i( self, invite_id ):
    """
    Redirect to the invite redemption URL, based on the given invite id. The sole purpose of this
    method is to shorten invite redemption URLs sent by email so email clients don't wrap them.
    """
    # if the value looks like an id, it's an invite id, so redirect
    try:
      validator = Valid_id()
      invite_id = validator( invite_id )
    except ValueError:
      raise cherrypy.NotFound

    return dict(
      redirect = u"/users/redeem_invite/%s" % invite_id,
    )

  @expose()
  def d( self, download_access_id ):
    """
    Redirect to the product download thanks URL, based on the given download access id. The sole
    purpose of this method is to shorten product download URLs sent by email so email clients don't
    wrap them.
    """
    # if the value looks like an id, it's a download access id, so redirect
    try:
      validator = Valid_id()
      download_access_id = validator( download_access_id )
    except ValueError:
      raise cherrypy.NotFound

    return dict(
      redirect = u"/users/thanks_download?access_id=%s" % download_access_id,
    )

  @expose( view = Front_page )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @update_auth
  @validate(
    user_id = Valid_id( none_okay = True ),
  )
  def index( self, user_id ):
    """
    Provide the information necessary to display the web site's front page, potentially performing
    a redirect to the https version of the page or the user's first notebook.
    """
    https_url = self.__settings[u"luminotes.https_url"]
    https_proxy_ip = self.__settings[u"luminotes.https_proxy_ip"]

    # if the server is configured to auto-login a particular user, log that user in and redirect to
    # their first notebook
    auto_login_username = self.__settings[u"luminotes.auto_login_username"]
    if auto_login_username:
      user = self.__database.select_one( User, User.sql_load_by_username( auto_login_username ), use_cache = True )

      if user and user.username:
        first_notebook = self.__database.select_one( Notebook, user.sql_load_notebooks( parents_only = True, undeleted_only = True ) )
        if first_notebook:
          return dict(
            redirect = u"/notebooks/%s" % first_notebook.object_id,
            authenticated = user,
          )

    # if the user is logged in and the HTTP request has no referrer, then redirect to the user's
    # first notebook
    if user_id:
      referer = cherrypy.request.headerMap.get( u"Referer" )
      if not referer:
        user = self.__database.load( User, user_id )

        if user and user.username:
          first_notebook = self.__database.select_one( Notebook, user.sql_load_notebooks( parents_only = True, undeleted_only = True ) )
          if first_notebook:
            return dict( redirect = u"%s/notebooks/%s" % ( https_url, first_notebook.object_id ) )
      
      # if the user is logged in and not using https, then redirect to the https version of the page (if available)
      if https_url and cherrypy.request.remote_addr != https_proxy_ip:
        return dict( redirect = u"%s/" % https_url )

    result = self.__users.current( user_id )
    parents = [ notebook for notebook in result[ u"notebooks" ] if notebook.trash_id and not notebook.deleted ]
    if len( parents ) > 0:
      result[ "first_notebook" ] = parents[ 0 ]
    else:
      result[ "first_notebook" ] = None

    return result

  @expose( view = Tour_page )
  @end_transaction
  @grab_user_id
  @validate(
    user_id = Valid_id( none_okay = True ),
  )
  def tour( self, user_id ):
    result = self.__users.current( user_id )
    parents = [ notebook for notebook in result[ u"notebooks" ] if notebook.trash_id and not notebook.deleted ]
    if len( parents ) > 0:
      result[ "first_notebook" ] = parents[ 0 ]
    else:
      result[ "first_notebook" ] = None

    return result

  @expose()
  def take_a_tour( self ):
    return dict( redirect = u"/tour" )

  @expose( view = Main_page )
  @end_transaction
  @grab_user_id
  @validate(
    note_id = Valid_id( none_okay = True ),
    user_id = Valid_id( none_okay = True ),
  )
  def guide( self, note_id = None, user_id = None ):
    """
    Provide the information necessary to display the Luminotes user guide.

    @type note_id: unicode or NoneType
    @param note_id: id of single note to load (optional)
    @rtype: unicode
    @return: rendered HTML page
    @raise Validation_error: one of the arguments is invalid
    """
    result = self.__users.current( user_id )
    anon_result = self.__users.current( None )
    guide_notebooks = [ nb for nb in anon_result[ "notebooks" ] if nb.name == u"Luminotes user guide" ]

    result.update( self.__notebooks.contents( guide_notebooks[ 0 ].object_id, user_id = user_id ) )

    # if a single note was requested, just return that one note
    if note_id:
      result[ "startup_notes" ] = [ note for note in result[ "startup_notes" ] if note.object_id == note_id ]

    return result

  @expose( view = Main_page )
  @end_transaction
  @grab_user_id
  @validate(
    user_id = Valid_id( none_okay = True ),
  )
  def privacy( self, user_id = None ):
    """
    Provide the information necessary to display the Luminotes privacy policy.

    @rtype: unicode
    @return: rendered HTML page
    @raise Validation_error: one of the arguments is invalid
    """
    result = self.__users.current( user_id )
    anon_result = self.__users.current( None )
    privacy_notebooks = [ nb for nb in anon_result[ "notebooks" ] if nb.name == u"Luminotes privacy policy" ]

    result.update( self.__notebooks.contents( privacy_notebooks[ 0 ].object_id, user_id = user_id ) )

    return result

  @expose( view = Upgrade_page )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    user_id = Valid_id( none_okay = True ),
  )
  def pricing( self, user_id = None ):
    """
    Provide the information necessary to display the Luminotes pricing page.
    """
    result = self.__users.current( user_id )
    parents = [ notebook for notebook in result[ u"notebooks" ] if notebook.trash_id and not notebook.deleted ]
    if len( parents ) > 0:
      result[ "first_notebook" ] = parents[ 0 ]
    else:
      result[ "first_notebook" ] = None

    result[ "rate_plans" ] = self.__settings[u"luminotes.rate_plans"]
    result[ "unsubscribe_button" ] = self.__settings[u"luminotes.unsubscribe_button"]

    return result

  @expose()
  def upgrade( self ):
    return dict(
      redirect = u"/pricing",
    )

  @expose()
  def support( self ):
    return dict(
      redirect = u"/community",
    )

  @expose( view = Download_page )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    upgrade = Valid_bool( none_okay = True ),
    user_id = Valid_id( none_okay = True ),
  )
  def download( self, upgrade = False, user_id = None ):
    """
    Provide the information necessary to display the Luminotes download page.
    """
    result = self.__users.current( user_id )
    parents = [ notebook for notebook in result[ u"notebooks" ] if notebook.trash_id and not notebook.deleted ]
    if len( parents ) > 0:
      result[ "first_notebook" ] = parents[ 0 ]
    else:
      result[ "first_notebook" ] = None

    result[ "download_products" ] = self.__settings[u"luminotes.download_products" ]

    referer = cherrypy.request.headerMap.get( u"Referer" )
    result[ "upgrade" ] = upgrade or ( referer and u"localhost:" in referer )

    return result

  # TODO: move this method to controller.Notebooks, and maybe give it a more sensible name
  @expose( view = Json )
  @end_transaction
  def next_id( self ):
    """
    Return the next available database object id for a new note. This id is guaranteed to be unique
    among all existing notes.

    @rtype: json dict
    @return: { 'next_id': nextid }
    """
    next_id = self.__database.next_id( Note )

    return dict(
      next_id = next_id,
    )

  @expose( view = Json )
  def ping( self ):
    return dict(
      response = u"pong",
    )

  @expose( view = Json )
  def shutdown( self ):
    # this is typically only allowed in the desktop configuration
    if self.__settings[u"luminotes.allow_shutdown_command" ] is not True:
      return dict()

    cherrypy.server.stop()

    return dict()

  @expose( view = Close_page )
  def close( self ):
    # this is typically only allowed in the desktop configuration
    if self.__settings[u"luminotes.allow_shutdown_command"] is not True:
      return dict()

    cherrypy.server.stop()

    return dict()

  def _cp_on_http_error( self, status, message ):
    """
    CherryPy HTTP error handler, used to display page not found and generic error pages.
    """
    support_email = self.__settings[u"luminotes.support_email"]

    if status == 404:
      cherrypy.response.headerMap[ u"Status" ] = u"404 Not Found"
      cherrypy.response.status = status
      cherrypy.response.body = [ unicode( Not_found_page( support_email ) ) ]
      return

    import traceback
    if not self.__suppress_exceptions:
      cherrypy.log( traceback.format_exc() )
    self.report_traceback()

    import sys
    error = sys.exc_info()[ 1 ]
    if hasattr( error, "to_dict" ):
      error_message = error.to_dict().get( u"error" )
    else:
      error_message = None

    cherrypy.response.body = [ unicode( Error_page( support_email, message = error_message ) ) ]

  def report_traceback( self ):
    """
    If a support email address is configured, send it an email with the current traceback.
    """
    support_email = self.__settings[u"luminotes.support_email"]
    if not support_email: return False

    import smtplib
    import traceback
    from email import Message
    
    message = Message.Message()
    message[ u"From" ] = support_email
    message[ u"To" ] = support_email
    message[ u"Subject" ] = u"Luminotes traceback"
    message.set_payload(
      u"requested URL: %s\n" % cherrypy.request.browser_url +
      u"user id: %s\n" % cherrypy.session.get( "user_id" ) +
      u"username: %s\n\n" % cherrypy.session.get( "username" ) +
      traceback.format_exc()
    )

    # send the message out through localhost's smtp server
    server = smtplib.SMTP()
    server.connect()
    server.sendmail( message[ u"From" ], [ support_email ], message.as_string() )
    server.quit()

    return True

  database = property( lambda self: self.__database )
  notebooks = property( lambda self: self.__notebooks )
  users = property( lambda self: self.__users )
  groups = property( lambda self: self.__groups )
  files = property( lambda self: self.__files )
  forums = property( lambda self: self.__forums )
  blog = property( lambda self: self.__blog )
