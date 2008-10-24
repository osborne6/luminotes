import cherrypy
from model.User import User
from model.Notebook import Notebook
from Expose import expose
from Validate import validate, Valid_string
from Database import Valid_id, end_transaction
from Users import grab_user_id
from Notebooks import Notebooks
from view.Forums_page import Forums_page
from view.Forum_page import Forum_page
from view.Main_page import Main_page


class Forums( object ):
  """
  Controller for dealing with discussion forums, corresponding to the "/forums" URL.
  """
  def __init__( self, database, notebooks, users ):
    """
    Create a new Forums object.

    @type database: controller.Database
    @param database: database that forums are stored in
    @type notebooks: controller.Users
    @param notebooks: controller for all notebooks
    @type users: controller.Users
    @param users: controller for all users
    @rtype: Forums
    @return: newly constructed Forums
    """
    self.__database = database
    self.__notebooks = notebooks
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

    @type user_id: unicode or NoneType
    @param user_id: id of the current user
    """
    result = self.__users.current( user_id )
    parents = [ notebook for notebook in result[ u"notebooks" ] if notebook.trash_id and not notebook.deleted ]
    if len( parents ) > 0:
      result[ "first_notebook" ] = parents[ 0 ]
    else:
      result[ "first_notebook" ] = None

    return result

  @expose( view = Forum_page )
  @end_transaction
  @grab_user_id
  @validate(
    forum_name = Valid_string( max = 100 ),
    user_id = Valid_id( none_okay = True ),
  )
  def default( self, forum_name, user_id ):
    """
    Provide the information necessary to display the current threads within a forum.

    @type forum_name: unicode
    @param forum_name: name of the forum to display
    @type user_id: unicode or NoneType
    @param user_id: id of the current user
    """
    result = self.__users.current( user_id )
    parents = [ notebook for notebook in result[ u"notebooks" ] if notebook.trash_id and not notebook.deleted ]
    if len( parents ) > 0:
      result[ "first_notebook" ] = parents[ 0 ]
    else:
      result[ "first_notebook" ] = None

    anonymous = self.__database.select_one( User, User.sql_load_by_username( u"anonymous" ), use_cache = True )
    if anonymous is None:
      raise Access_error()

    # TODO: this needs to sort by either thread/note creation or modification date
    threads = self.__database.select_many(
      Notebook,
      anonymous.sql_load_notebooks(
        parents_only = False, undeleted_only = True, tag_name = u"forum", tag_value = forum_name
      )
    )

    # if there are no matching threads, then this forum doesn't exist
    if len( threads ) == 0:
      raise cherrypy.NotFound

    result[ "forum_name" ] = forum_name
    result[ "threads" ] = threads
    return result

  # threads() is just an alias for Notebooks.default()
  def threads( self, *args, **kwargs ):
    return self.__notebooks.default( *args, **kwargs )
  threads.exposed = True
