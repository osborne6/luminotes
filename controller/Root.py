import cherrypy

from Scheduler import Scheduler
from Expose import expose
from Validate import validate
from Async import async
from Notebooks import Notebooks
from Users import Users
from Updater import update_client, wait_for_update
from Database import Valid_id
from view.Main_page import Main_page
from view.Json import Json
from view.Error_page import Error_page
from view.Not_found_page import Not_found_page


class Root( object ):
  """
  The root of the controller hierarchy, corresponding to the "/" URL.
  """
  def __init__( self, scheduler, database, settings ):
    """
    Create a new Root object with the given settings.

    @type scheduler: controller.Scheduler
    @param scheduler: scheduler to use for asynchronous calls
    @type database: controller.Database
    @param database: database to use for all controllers
    @type settings: dict
    @param settings: CherryPy-style settings with top-level "global" key
    @rtype: Root
    @return: newly constructed Root
    """
    self.__scheduler = scheduler
    self.__database = database
    self.__settings = settings
    self.__users = Users(
      scheduler,
      database,
      settings[ u"global" ].get( u"luminotes.http_url", u"" ),
      settings[ u"global" ].get( u"luminotes.https_url", u"" ),
      settings[ u"global" ].get( u"luminotes.support_email", u"" ),
      settings[ u"global" ].get( u"luminotes.rate_plans", [] ),
    )
    self.__notebooks = Notebooks( scheduler, database, self.__users )

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
  def index( self ):
    """
    Provide the information necessary to display the web site's front page, potentially performing
    a redirect to the https version of the page.
    """
    # if the user is logged in and not using https, then redirect to the https version of the page (if available)
    https_url = self.__settings[ u"global" ].get( u"luminotes.https_url" )
    https_proxy_ip = self.__settings[ u"global" ].get( u"luminotes.https_proxy_ip" )
    
    if cherrypy.session.get( "user_id" ) and https_url and cherrypy.request.remote_addr != https_proxy_ip:
      return dict( redirect = https_url )

    return dict()

  @expose( view = Json )
  @wait_for_update
  @async
  @update_client
  def next_id( self ):
    """
    Return the next available database object id. This id is guaranteed to be unique to the
    database.

    @rtype: json dict
    @return: { 'next_id': nextid }
    """
    self.__database.next_id( self.__scheduler.thread )
    next_id = ( yield Scheduler.SLEEP )

    yield dict(
      next_id = next_id,
    )

  def _cp_on_http_error( self, status, message ):
    """
    CherryPy HTTP error handler, used to display page not found and generic error pages.
    """
    if status == 404:
      cherrypy.response.headerMap[ u"Status" ] = u"404 Not Found"
      cherrypy.response.status = status
      cherrypy.response.body = [ unicode( Not_found_page( self.__settings[ u"global" ].get( u"luminotes.support_email" ) ) ) ]
      return

    import sys
    import traceback
    traceback.print_exc()

    exc_info = sys.exc_info()
    if exc_info:
      message = exc_info[ 1 ].message
    else:
      message = None

    cherrypy.response.body = [ unicode( Error_page(
      self.__settings[ u"global" ].get( u"luminotes.support_email" ),
      message,
    ) ) ]

  scheduler = property( lambda self: self.__scheduler )
  database = property( lambda self: self.__database )
  notebooks = property( lambda self: self.__notebooks )
  users = property( lambda self: self.__users )
