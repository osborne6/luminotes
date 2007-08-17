import cherrypy
from Scheduler import Scheduler
from Expose import expose
from Validate import validate, Valid_string, Validation_error, Valid_bool
from Database import Valid_id
from Users import grab_user_id
from Updater import wait_for_update, update_client
from Expire import strongly_expire
from Html_nuker import Html_nuker
from Async import async
from model.Notebook import Notebook
from model.Note import Note
from view.Main_page import Main_page
from view.Json import Json
from view.Note_page import Note_page
from view.Html_file import Html_file


class Access_error( Exception ):
  def __init__( self, message = None ):
    if message is None:
      message = u"You don't have access to this notebook."

    Exception.__init__( self, message )
    self.__message = message

  def to_dict( self ):
    return dict(
      error = self.__message
    )


class Notebooks( object ):
  """
  Controller for dealing with notebooks and their notes, corresponding to the "/notebooks" URL.
  """
  def __init__( self, scheduler, database ):
    """
    Create a new Notebooks object.

    @type scheduler: controller.Scheduler
    @param scheduler: scheduler to use for asynchronous calls
    @type database: controller.Database
    @param database: database that notebooks are stored in
    @rtype: Notebooks
    @return: newly constructed Notebooks
    """
    self.__scheduler = scheduler
    self.__database = database

  @expose( view = Main_page )
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    revision = Valid_string( min = 19, max = 30 ),
  )
  def default( self, notebook_id, note_id = None, revision = None ):
    """
    Provide the information necessary to display the page for a particular notebook. If a
    particular note id is given without a revision, then the most recent version of that note is
    displayed.

    @type notebook_id: unicode
    @param notebook_id: id of the notebook to display
    @type note_id: unicode or NoneType
    @param note_id: id of single note in this notebook to display (optional)
    @type revision: unicode or NoneType
    @param revision: revision timestamp of the provided note (optional)
    @rtype: unicode
    @return: rendered HTML page
    """
    return dict(
      notebook_id = notebook_id,
      note_id = note_id,
      revision = revision,
    )

  @expose( view = Json )
  @strongly_expire
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id( none_okay = True ),
    revision = Valid_string( min = 0, max = 30 ),
    user_id = Valid_id( none_okay = True ),
  )
  def contents( self, notebook_id, note_id = None, revision = None, user_id = None ):
    """
    Return the information on particular notebook, including the contents of its startup notes.
    Optionally include the contents of a single requested note as well.

    @type notebook_id: unicode
    @param notebook_id: id of notebook to return
    @type note_id: unicode or NoneType
    @param note_id: id of single note in this notebook to return (optional)
    @type revision: unicode or NoneType
    @param revision: revision timestamp of the provided note (optional)
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'notebook': notebookdict, 'note': notedict or None }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if notebook is None:
      note = None
    else:
      note = notebook.lookup_note( note_id )

    if revision:
      self.__database.load( note_id, self.__scheduler.thread, revision )
      note = ( yield Scheduler.SLEEP )

    yield dict(
      notebook = notebook,
      note = note,
    )

  @expose( view = Json )
  @strongly_expire
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    revision = Valid_string( min = 19, max = 30 ),
    user_id = Valid_id( none_okay = True ),
  )
  def load_note( self, notebook_id, note_id, revision = None, user_id = None ):
    """
    Return the information on a particular note by its id.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_id: unicode
    @param note_id: id of note to return
    @type revision: unicode or NoneType
    @param revision: revision timestamp of the note (optional)
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'note': notedict or None }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if notebook is None:
      note = None
    else:
      note = notebook.lookup_note( note_id )

    if revision:
      self.__database.load( note_id, self.__scheduler.thread, revision )
      note = ( yield Scheduler.SLEEP )

    yield dict(
      note = note,
    )

  @expose( view = Json )
  @strongly_expire
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    note_title = Valid_string( min = 1, max = 500 ),
    user_id = Valid_id( none_okay = True ),
  )
  def load_note_by_title( self, notebook_id, note_title, user_id ):
    """
    Return the information on a particular note by its title.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_title: unicode
    @param note_title: title of the note to return
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'note': notedict or None }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if notebook is None:
      note = None
    else:
      note = notebook.lookup_note_by_title( note_title )

    yield dict(
      note = note,
    )

  @expose( view = Json )
  @strongly_expire
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    note_title = Valid_string( min = 1, max = 500 ),
    user_id = Valid_id( none_okay = True ),
  )
  def lookup_note_id( self, notebook_id, note_title, user_id ):
    """
    Return a note's id by looking up its title.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_title: unicode
    @param note_title: title of the note id to return
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'note_id': noteid or None }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if notebook is None:
      note = None
    else:
      note = notebook.lookup_note_by_title( note_title )

    yield dict(
      note_id = note and note.object_id or None,
    )

  @expose( view = Json )
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    contents = Valid_string( min = 1, max = 25000, escape_html = False ),
    startup = Valid_bool(),
    user_id = Valid_id( none_okay = True ),
  )
  def save_note( self, notebook_id, note_id, contents, startup, user_id ):
    """
    Save a new revision of the given note. This function will work both for creating a new note and
    for updating an existing note. If the note exists and the given contents are identical to the
    existing contents, then no saving takes place and a new_revision of None is returned. Otherwise
    this method returns the timestamp of the new revision.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_id: unicode
    @param note_id: id of note to save
    @type contents: unicode
    @param contents: new textual contents of the note, including its title
    @type startup: bool
    @param startup: whether the note should be displayed on startup
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'new_revision': new revision of saved note, or None }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      raise Access_error()

    self.__database.load( note_id, self.__scheduler.thread )
    note = ( yield Scheduler.SLEEP )

    # if the note is already in the database, load it and update it. otherwise, create it
    if note and note in notebook.notes:
      orig_revision = note.revision
      notebook.update_note( note, contents )
    else:
      orig_revision = None
      note = Note( note_id, contents )
      notebook.add_note( note )

    if startup:
      notebook.add_startup_note( note )
    else:
      notebook.remove_startup_note( note )

    self.__database.save( notebook )

    if note.revision == orig_revision:
      yield dict( new_revision = None )
    else:
      yield dict( new_revision = note.revision )

  @expose( view = Json )
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def add_startup_note( self, notebook_id, note_id, user_id ):
    """
    Designate a particular note to be shown upon startup, e.g. whenever its notebook is displayed.
    The given note must already be within this notebook.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_id: unicode
    @param note_id: id of note to show on startup
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: {}
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      raise Access_error()

    self.__database.load( note_id, self.__scheduler.thread )
    note = ( yield Scheduler.SLEEP )

    if note:
      notebook.add_startup_note( note )
      self.__database.save( notebook )

    yield dict()

  @expose( view = Json )
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def remove_startup_note( self, notebook_id, note_id, user_id ):
    """
    Prevent a particular note from being shown on startup, e.g. whenever its notebook is displayed.
    The given note must already be within this notebook.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_id: unicode
    @param note_id: id of note to no longer show on startup
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: {}
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      raise Access_error()

    self.__database.load( note_id, self.__scheduler.thread )
    note = ( yield Scheduler.SLEEP )

    if note:
      notebook.remove_startup_note( note )
      self.__database.save( notebook )

    yield dict()

  @expose( view = Json )
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def delete_note( self, notebook_id, note_id, user_id ):
    """
    Delete the given note from its notebook and move it to the notebook's trash. The note is added
    as a startup note within the trash.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_id: unicode
    @param note_id: id of note to delete
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: {}
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      raise Access_error()

    self.__database.load( note_id, self.__scheduler.thread )
    note = ( yield Scheduler.SLEEP )

    if note:
      notebook.remove_note( note )

      if notebook.trash:
        note.deleted_from = notebook.object_id
        notebook.trash.add_note( note )
        notebook.trash.add_startup_note( note )

      self.__database.save( notebook )

    yield dict()

  @expose( view = Json )
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def undelete_note( self, notebook_id, note_id, user_id ):
    """
    Undelete the given note from the trash, moving it back into its notebook. The note is added
    as a startup note within its notebook.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note was in
    @type note_id: unicode
    @param note_id: id of note to undelete
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: {}
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      raise Access_error()

    self.__database.load( note_id, self.__scheduler.thread )
    note = ( yield Scheduler.SLEEP )

    if note and notebook.trash:
      if note.deleted_from != notebook_id:
        raise Access_error()

      notebook.trash.remove_note( note )

      note.deleted_from = None
      notebook.add_note( note )
      notebook.add_startup_note( note )

      self.__database.save( notebook )

    yield dict()

  @expose( view = Note_page )
  @validate( id = Valid_string( min = 1, max = 100 ) )
  def blank_note( self, id ):
    """
    Provide the information necessary to display a blank note frame to be filled in by the client.

    @param id: unicode
    @type id: id of the note
    @rtype: unicode
    @return: rendered HTML page
    @raise Validation_error: the argument is invalid
    """
    return dict( id = id )

  @expose( view = Json )
  @strongly_expire
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    search_text = Valid_string( min = 0, max = 100 ),
    user_id = Valid_id( none_okay = True ),
    titles_only = Valid_bool(),
  )
  def search( self, notebook_id, search_text, titles_only, user_id ):
    """
    Search the notes within a particular notebook for the given search text. Note that the search
    is case-insensitive, and all HTML tags are ignored. The matching notes are returned with title
    matches first, followed by all other matches.

    @type notebook_id: unicode
    @param notebook_id: id of notebook to search
    @type search_text: unicode
    @param search_text: search term
    @type titles_only: bool
    @param titles_only: if true, only search titles. if false, search all note titles and contents
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'notes': [ matching notes ] }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      raise Access_error()

    search_text = search_text.lower()
    title_matches = []
    content_matches = []
    nuker = Html_nuker()

    if len( search_text ) > 0:
      for note in notebook.notes:
      	if note is None: continue
        if search_text in nuker.nuke( note.title ).lower():
          title_matches.append( note )
        elif not titles_only and search_text in nuker.nuke( note.contents ).lower():
          content_matches.append( note )

    notes = title_matches + content_matches

    yield dict(
      notes = notes,
    )

  @expose( view = Json )
  @strongly_expire
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def recent_notes( self, notebook_id, user_id ):
    """
    Return several of the most recently updated notes, sorting by reverse chronological order.

    @type notebook_id: unicode
    @param notebook_id: id of notebook to pull recent notes from
    @type user_id: unicode
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'notes': [ recent notes ] }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      raise Access_error()

    RECENT_COUNT = 10
    notes = [ note for note in notebook.notes if note is not None ]
    notes.sort( lambda a, b: cmp( b.revision, a.revision ) )

    yield dict(
      notes = notes[ :RECENT_COUNT ],
    )

  @expose( view = Html_file )
  @strongly_expire
  @wait_for_update
  @grab_user_id
  @async
  @update_client
  @validate(
    notebook_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def download_html( self, notebook_id, user_id ):
    """
    Download the entire contents of the given notebook as a stand-alone HTML page (no Javascript).

    @type notebook_id: unicode
    @param notebook_id: id of notebook to download
    @type user_id: unicode
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: unicode
    @return: rendered HTML page
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    self.check_access( notebook_id, user_id, self.__scheduler.thread )
    if not ( yield Scheduler.SLEEP ):
      raise Access_error()

    self.__database.load( notebook_id, self.__scheduler.thread )
    notebook = ( yield Scheduler.SLEEP )

    if not notebook:
      raise Access_error()

    normal_notes = list( set( notebook.notes ) - set( notebook.startup_notes ) )
    normal_notes.sort( lambda a, b: -cmp( a.revision, b.revision ) )
    
    yield dict(
      notebook_name = notebook.name,
      notes = [ note for note in notebook.startup_notes + normal_notes if note is not None ],
    )

  @async
  def check_access( self, notebook_id, user_id, callback ):
    # check if the anonymous user has access to this notebook
    self.__database.load( u"User anonymous", self.__scheduler.thread )
    anonymous = ( yield Scheduler.SLEEP )

    access = False
    if anonymous.has_access( notebook_id ):
      access = True

    if user_id:
      # check if the currently logged in user has access to this notebook
      self.__database.load( user_id, self.__scheduler.thread )
      user = ( yield Scheduler.SLEEP )

      if user and user.has_access( notebook_id ):
        access = True

    yield callback, access

  scheduler = property( lambda self: self.__scheduler )
