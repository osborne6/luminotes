from Expose import expose
from Validate import validate
from Database import Valid_id, end_transaction
from Users import grab_user_id
from view.Forums_page import Forums_page


class Forums( object ):
  """
  Controller for dealing with discussion forums, corresponding to the "/forums" URL.
  """
  def __init__( self, database, users ):
    """
    Create a new Forums object.

    @type database: controller.Database
    @param database: database that forums are stored in
    @type users: controller.Users
    @param users: controller for all users
    @rtype: Forums
    @return: newly constructed Forums
    """
    self.__database = database
    self.__users = users

  @expose( view = Forums_page )
  @end_transaction
  @grab_user_id
  @validate(
    user_id = Valid_id( none_okay = True ),
  )
  def index( self, user_id ):
    """
    Provide the information necessary to display the listing of available forums (currently hard-coded).
    """
    result = self.__users.current( user_id )
    parents = [ notebook for notebook in result[ u"notebooks" ] if notebook.trash_id and not notebook.deleted ]
    if len( parents ) > 0:
      result[ "first_notebook" ] = parents[ 0 ]
    else:
      result[ "first_notebook" ] = None

    return result
