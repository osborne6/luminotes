import cherrypy

from Expose import expose
from Expire import strongly_expire
from Validate import validate, Valid_int
from Notebooks import Notebooks
from Users import Users, grab_user_id
from Database import Valid_id
from model.Note import Note
from model.Notebook import Notebook
from model.User import User
from view.Main_page import Main_page
from view.Notebook_rss import Notebook_rss
from view.Json import Json
from view.Error_page import Error_page
from view.Not_found_page import Not_found_page


class Root( object ):
  """
  The root of the controller hierarchy, corresponding to the "/" URL.
  """
  def __init__( self, database, settings ):
    """
    Create a new Root object with the given settings.

    @type database: controller.Database
    @param database: database to use for all controllers
    @type settings: dict
    @param settings: CherryPy-style settings with top-level "global" key
    @rtype: Root
    @return: newly constructed Root
    """
    self.__database = database
    self.__settings = settings
    self.__users = Users(
      database,
      settings[ u"global" ].get( u"luminotes.http_url", u"" ),
      settings[ u"global" ].get( u"luminotes.https_url", u"" ),
      settings[ u"global" ].get( u"luminotes.support_email", u"" ),
      settings[ u"global" ].get( u"luminotes.rate_plans", [] ),
    )
    self.__notebooks = Notebooks( database, self.__users )

  @expose( Main_page )
  @validate(
    note_title = unicode,
  )
  def default( self, note_title ):
    """
    Convenience method for accessing a note in the main notebook by name rather than by note id.
    """
    # if the user is logged in and not using https, and they request the sign up or login note, then
    # redirect to the https version of the page (if available)
    https_url = self.__settings[ u"global" ].get( u"luminotes.https_url" )
    https_proxy_ip = self.__settings[ u"global" ].get( u"luminotes.https_proxy_ip" )
    
    if note_title in ( u"sign_up", u"login" ) and https_url and cherrypy.request.remote_addr != https_proxy_ip:
      return dict( redirect = u"%s/%s" % ( https_url, note_title ) )

    result = self.__users.current( user_id = None )
    first_notebook = result[ u"notebooks" ][ 0 ]
    user_id = result[ u"user" ].object_id

    note_title = note_title.replace( u"_", " " )
    note = self.__database.select_one( Note, first_notebook.sql_load_note_by_title( note_title ) )
    if not note:
      raise cherrypy.NotFound

    result.update( self.__notebooks.contents( first_notebook.object_id, user_id = user_id, note_id = note.object_id ) )

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

  @expose( view = Main_page )
  @strongly_expire
  @grab_user_id
  @validate(
    user_id = Valid_id( none_okay = True ),
  )
  def index( self, user_id ):
    """
    Provide the information necessary to display the web site's front page, potentially performing
    a redirect to the https version of the page.
    """
    # if the user is logged in and not using https, then redirect to the https version of the page (if available)
    https_url = self.__settings[ u"global" ].get( u"luminotes.https_url" )
    https_proxy_ip = self.__settings[ u"global" ].get( u"luminotes.https_proxy_ip" )
    
    if cherrypy.session.get( "user_id" ) and https_url and cherrypy.request.remote_addr != https_proxy_ip:
      return dict( redirect = https_url )

    result = self.__users.current( user_id )
    main_notebooks = [ nb for nb in result[ "notebooks" ] if nb.name == u"Luminotes" ]

    result.update( self.__notebooks.contents( main_notebooks[ 0 ].object_id, user_id = user_id ) )

    return result

  @expose( view = Main_page, rss = Notebook_rss )
  @grab_user_id
  @validate(
    start = Valid_int( min = 0 ),
    count = Valid_int( min = 1, max = 50 ),
    note_id = Valid_id( none_okay = True ),
    user_id = Valid_id( none_okay = True ),
  )
  def blog( self, start = 0, count = 5, note_id = None, user_id = None ):
    """
    Provide the information necessary to display the blog notebook with notes in reverse
    chronological order.

    @type start: unicode or NoneType
    @param start: index of recent note to start with (defaults to 0, the most recent note)
    @type count: int or NoneType
    @param count: number of recent notes to display (defaults to 10 notes)
    @rtype: unicode
    @return: rendered HTML page
    @raise Validation_error: one of the arguments is invalid
    """
    result = self.__users.current( user_id )
    blog_notebooks = [ nb for nb in result[ "notebooks" ] if nb.name == u"Luminotes blog" ]

    result.update( self.__notebooks.load_recent_notes( blog_notebooks[ 0 ].object_id, start, count, user_id ) )

    # if a single note was requested, just return that one note
    if note_id:
      result[ "notes" ] = [ note for note in result[ "notes" ] if note.object_id == note_id ]

    result[ "http_url" ] = self.__settings[ u"global" ].get( u"luminotes.http_url", u"" )

    return result

  @expose( view = Main_page )
  @grab_user_id
  @validate(
    user_id = Valid_id( none_okay = True ),
  )
  def guide( self, user_id = None ):
    """
    Provide the information necessary to display the Luminotes user guide.

    @rtype: unicode
    @return: rendered HTML page
    @raise Validation_error: one of the arguments is invalid
    """
    result = self.__users.current( user_id )
    guide_notebooks = [ nb for nb in result[ "notebooks" ] if nb.name == u"Luminotes user guide" ]

    result.update( self.__notebooks.contents( guide_notebooks[ 0 ].object_id, user_id = user_id ) )

    return result

  @expose( view = Main_page )
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
    privacy_notebooks = [ nb for nb in result[ "notebooks" ] if nb.name == u"Luminotes privacy policy" ]

    result.update( self.__notebooks.contents( privacy_notebooks[ 0 ].object_id, user_id = user_id ) )

    return result

  # TODO: move this method to controller.Notebooks, and maybe give it a more sensible name
  @expose( view = Json )
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

  def _cp_on_http_error( self, status, message ):
    """
    CherryPy HTTP error handler, used to display page not found and generic error pages.
    """
    support_email = self.__settings[ u"global" ].get( u"luminotes.support_email" )

    if status == 404:
      cherrypy.response.headerMap[ u"Status" ] = u"404 Not Found"
      cherrypy.response.status = status
      cherrypy.response.body = [ unicode( Not_found_page( support_email ) ) ]
      return

    import traceback
    traceback.print_exc()
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
    support_email = self.__settings[ u"global" ].get( u"luminotes.support_email" )
    if not support_email: return False

    import smtplib
    import traceback
    from email import Message
    
    message = Message.Message()
    message[ u"from" ] = support_email
    message[ u"to" ] = support_email
    message[ u"subject" ] = u"Luminotes traceback"
    message.set_payload(
      u"requested URL: %s\n" % cherrypy.request.browser_url +
      u"user id: %s\n" % cherrypy.session.get( "user_id" ) +
      u"username: %s\n\n" % cherrypy.session.get( "username" ) +
      traceback.format_exc()
    )

    # send the message out through localhost's smtp server
    server = smtplib.SMTP()
    server.connect()
    server.sendmail( message[ u"from" ], [ support_email ], message.as_string() )
    server.quit()

    return True

  database = property( lambda self: self.__database )
  notebooks = property( lambda self: self.__notebooks )
  users = property( lambda self: self.__users )
