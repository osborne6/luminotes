import cherrypy

from Scheduler import Scheduler
from Expose import expose
from Validate import validate
from Async import async
from Notebooks import Notebooks
from Users import Users
from Updater import update_client, wait_for_update
from view.Main_page import Main_page
from view.Json import Json
from view.Error_page import Error_page
from view.Not_found_page import Not_found_page


class Root( object ):
  def __init__( self, scheduler, database ):
    self.__scheduler = scheduler
    self.__database = database
    self.__notebooks = Notebooks( scheduler, database )
    self.__users = Users( scheduler, database )

  @expose( view = Main_page )
  def index( self ):
    """
    Provide the information necessary to display the web site's front page.
    """
    return dict()

  @expose( view = Json )
  @wait_for_update
  @async
  @update_client
  def next_id( self ):
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
      cherrypy.response.body = [ unicode( Not_found_page() ) ]
      return

    import traceback
    traceback.print_exc()

    cherrypy.response.body = [ unicode( Error_page() ) ]

  scheduler = property( lambda self: self.__scheduler )
  database = property( lambda self: self.__database )
  notebooks = property( lambda self: self.__notebooks )
  users = property( lambda self: self.__users )
