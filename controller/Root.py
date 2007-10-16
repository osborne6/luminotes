import cherrypy

from Expose import expose
from Expire import strongly_expire
from Validate import validate
from Notebooks import Notebooks
from Users import Users, grab_user_id
from Database import Valid_id
from model.Note import Note
from view.Main_page import Main_page
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

  @expose()
  def default( self, password_reset_id ):
    # if the value looks like an id, assume it's a password reset id, and redirect
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
    first_notebook_id = result[ u"notebooks" ][ 0 ].object_id
    result.update( self.__notebooks.contents( first_notebook_id, user_id = user_id ) )

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

    # TODO: it'd be nice to send an email to myself with the traceback
    import traceback
    traceback.print_exc()

    cherrypy.response.body = [ unicode( Error_page( support_email ) ) ]

  database = property( lambda self: self.__database )
  notebooks = property( lambda self: self.__notebooks )
  users = property( lambda self: self.__users )
