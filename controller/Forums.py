import cherrypy
from model.User import User
from model.Notebook import Notebook
from model.Note import Note
from model.Tag import Tag
from Expose import expose
from Expire import strongly_expire
from Validate import validate, Valid_string, Valid_int
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
  @strongly_expire
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
  DEFAULT_THREAD_NAME = u"new discussion"

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
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    start = Valid_int( min = 0 ),
    count = Valid_int( min = 1, max = 50 ),
    user_id = Valid_id( none_okay = True ),
  )
  def index( self, start = 0, count = 50, user_id = None ):
    """
    Provide the information necessary to display the current threads within a forum (in reverse
    chronological order).

    @type start: integer or NoneType
    @param start: index of first forum thread to display (optional, defaults to 0)
    @type count: integer or NoneType
    @param count: how many forum threads to display (optional, defaults to quite a few)
    @type user_id: unicode or NoneType
    @param user_id: id of the current user
    @rtype: unicode
    @return: rendered HTML page
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

    # load a slice of the list of the threads in this forum, excluding those with a default name
    threads = self.__database.select_many(
      Notebook,
      anonymous.sql_load_notebooks(
        parents_only = False, undeleted_only = True, tag_name = u"forum", tag_value = self.__name,
        exclude_notebook_name = self.DEFAULT_THREAD_NAME, reverse = True,
        start = start, count = count,
      )
    )

    # if there are no matching threads, then this forum doesn't exist
    if len( threads ) == 0:
      raise cherrypy.NotFound

    # count the total number of threads in this forum, excluding those with a default name
    total_thread_count = self.__database.select_one(
      int,
      anonymous.sql_count_notebooks(
        parents_only = False, undeleted_only = True, tag_name = u"forum", tag_value = self.__name,
        exclude_notebook_name = self.DEFAULT_THREAD_NAME,
      )
    )

    result[ "forum_name" ] = self.__name
    result[ "threads" ] = threads
    result[ "start" ] = start
    result[ "count" ] = count
    result[ "total_thread_count" ] = total_thread_count
    return result

  @expose( view = Main_page )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    thread_id = Valid_id(),
    start = Valid_int( min = 0 ),
    count = Valid_int( min = 1, max = 50 ),
    note_id = Valid_id( none_okay = True ),
    user_id = Valid_id( none_okay = True ),
  )
  def default( self, thread_id, start = 0, count = 10, note_id = None, user_id = None ):
    """
    Provide the information necessary to display a forum thread.

    @type thread_id: unicode
    @param thread_id: id of thread notebook to display
    @type start: unicode or NoneType
    @param start: index of recent note to start with (defaults to 0, the most recent note)
    @type count: int or NoneType
    @param count: number of recent notes to display (defaults to 10 notes)
    @type note_id: unicode or NoneType
    @param note_id: id of single note to load (optional)
    @rtype: unicode
    @return: rendered HTML page
    @raise Validation_error: one of the arguments is invalid
    """
    result = self.__users.current( user_id )
    result.update( self.__notebooks.old_notes( thread_id, start, count, user_id ) )

    # if a single note was requested, just return that one note
    if note_id:
      result[ "notes" ] = [ note for note in result[ "notes" ] if note.object_id == note_id ]

    return result

  default.exposed = True

  @expose()
  @end_transaction
  @grab_user_id
  @validate(
    user_id = Valid_id( none_okay = True ),
  )
  def create_thread( self, user_id ):
    """
    Create a new forum thread with a blank post, and give the thread a default name. Then redirect
    to that new thread.

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
    thread = Notebook.create( thread_id, self.DEFAULT_THREAD_NAME, user_id = user.object_id )
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

    # create a blank post in which the user can  start off the thread
    note_id = self.__database.next_id( Notebook, commit = False )
    note = Note.create( note_id, u"<h3>", notebook_id = thread_id, startup = True, rank = 0, user_id = user_id )
    self.__database.save( note, commit = False )

    self.__database.commit()

    return dict(
      redirect = u"/forums/%s/%s" % ( self.__name, thread_id ),
    )
