import cherrypy
from model.User import User
from model.Notebook import Notebook
from model.Tag import Tag
from Expose import expose
from Validate import validate, Valid_string
from Database import Valid_id, end_transaction
from Users import grab_user_id
from Notebooks import Notebooks
from Users import Access_error
from view.Forums_page import Forums_page
from view.Forum_page import Forum_page
from view.Main_page import Main_page


class Forums( object ):
  """
  Controller for dealing with discussion forums, corresponding to the "/forums" URL.
  """
  def __init__( self, database, notebooks, users ):
    """
    Create a new Forums object, representing a collection of forums.

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

    self.__general = Forum( database, notebooks, users, u"general" )
    self.__support = Forum( database, notebooks, users, u"support" )

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

  general = property( lambda self: self.__general )
  support = property( lambda self: self.__support )


class Forum( object ):
  def __init__( self, database, notebooks, users, name ):
    """
    Create a new Forum object, representing a single forum.

    @type database: controller.Database
    @param database: database that forums are stored in
    @type notebooks: controller.Users
    @param notebooks: controller for all notebooks
    @type users: controller.Users
    @param users: controller for all users
    @type name: unicode
    @param name: one-word name of this forum
    @rtype: Forums
    @return: newly constructed Forums
    """
    self.__database = database
    self.__notebooks = notebooks
    self.__users = users
    self.__name = name

  @expose( view = Forum_page )
  @end_transaction
  @grab_user_id
  @validate(
    user_id = Valid_id( none_okay = True ),
  )
  def index( self, user_id ):
    """
    Provide the information necessary to display the current threads within a forum.

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

    threads = self.__database.select_many(
      Notebook,
      anonymous.sql_load_notebooks(
        parents_only = False, undeleted_only = True, tag_name = u"forum", tag_value = self.__name
      )
    )

    # put threads in reverse chronological order by creation date
    threads.reverse()

    # if there are no matching threads, then this forum doesn't exist
    if len( threads ) == 0:
      raise cherrypy.NotFound

    result[ "forum_name" ] = self.__name
    result[ "threads" ] = threads
    return result

  # default() is just an alias for Notebooks.default()
  def default( self, *args, **kwargs ):
    return self.__notebooks.default( *args, **kwargs )

  default.exposed = True

  @expose()
  @end_transaction
  @grab_user_id
  @validate(
    user_id = Valid_id( none_okay = True ),
  )
  def create_thread( self, user_id ):
    """
    Create a new forum post and give it a default name. Then redirect to that new post thread.

    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype dict
    @return { 'redirect': new_notebook_url }
    @raise Access_error: the current user doesn't have access to create a post
    @raise Validation_error: one of the arguments is invalid
    """
    if user_id is None:
      raise Access_error()

    user = self.__database.load( User, user_id )
    if user is None or not user.username or user.username == "anonymous":
      raise Access_error()

    anonymous = self.__database.select_one( User, User.sql_load_by_username( u"anonymous" ), use_cache = True )
    if anonymous is None:
      raise Access_error()

    # create the new notebook thread
    thread_id = self.__database.next_id( Notebook, commit = False )
    thread = Notebook.create( thread_id, u"new forum post", user_id = user.object_id )
    self.__database.save( thread, commit = False )

    # associate the forum tag with the new notebook thread
    tag = self.__database.select_one( Tag, Tag.sql_load_by_name( u"forum", user_id = anonymous.object_id ) )
    self.__database.execute(
      anonymous.sql_save_notebook_tag( thread_id, tag.object_id, value = self.__name ),
      commit = False,
    )

    # give the anonymous user access to the new notebook thread
    self.__database.execute(
      anonymous.sql_save_notebook( thread_id, read_write = True, owner = False, own_notes_only = True ),
      commit = False,
    )

    self.__database.commit()

    return dict(
      redirect = u"/forums/%s/%s" % ( self.__name, thread_id ),
    )
