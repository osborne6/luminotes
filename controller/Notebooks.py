import cherrypy
from datetime import datetime
from Expose import expose
from Validate import validate, Valid_string, Validation_error, Valid_bool
from Database import Valid_id, Valid_revision
from Users import grab_user_id
from Expire import strongly_expire
from Html_nuker import Html_nuker
from model.Notebook import Notebook
from model.Note import Note
from view.Main_page import Main_page
from view.Json import Json
from view.Html_file import Html_file


class Access_error( Exception ):
  def __init__( self, message = None ):
    if message is None:
      message = u"Sorry, you don't have access to do that."

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
  def __init__( self, database, users ):
    """
    Create a new Notebooks object.

    @type database: controller.Database
    @param database: database that notebooks are stored in
    @type users: controller.Users
    @param users: controller for all users, used here for updating storage utilization
    @rtype: Notebooks
    @return: newly constructed Notebooks
    """
    self.__database = database
    self.__users = users

  @expose( view = Main_page )
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    parent_id = Valid_id(),
    revision = Valid_revision(),
  )
  def default( self, notebook_id, note_id = None, parent_id = None, revision = None ):
    """
    Provide the information necessary to display the page for a particular notebook. If a
    particular note id is given without a revision, then the most recent version of that note is
    displayed.

    @type notebook_id: unicode
    @param notebook_id: id of the notebook to display
    @type note_id: unicode or NoneType
    @param note_id: id of single note in this notebook to display (optional)
    @type parent_id: unicode or NoneType
    @param parent_id: id of parent notebook to this notebook (optional)
    @type revision: unicode or NoneType
    @param revision: revision timestamp of the provided note (optional)
    @rtype: unicode
    @return: rendered HTML page
    """
    return dict(
      notebook_id = notebook_id,
      note_id = note_id,
      parent_id = parent_id,
      revision = revision,
    )

  @expose( view = Json )
  @strongly_expire
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id( none_okay = True ),
    revision = Valid_revision( none_okay = True ),
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
    @raise Access_error: the current user doesn't have access to the given notebook or note
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if not self.__users.check_access( user_id, notebook_id, read_write = True ):
      notebook.read_write = False

    if notebook is None:
      note = None
    elif note_id == u"blank":
      note = Note.create( note_id )
    else:
      note = self.__database.load( Note, note_id, revision )
      if note and note.notebook_id != notebook_id:
        raise Access_error()

    startup_notes = self.__database.select_many( Note, notebook.sql_load_startup_notes() )

    return dict(
      notebook = notebook,
      startup_notes = startup_notes,
      note = note,
    )

  @expose( view = Json )
  @strongly_expire
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    revision = Valid_revision(),
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
    @raise Access_error: the current user doesn't have access to the given notebook or note
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    note = self.__database.load( Note, note_id, revision )

    if note and note.notebook_id != notebook_id:
      raise Access_error()

    return dict(
      note = note,
    )

  @expose( view = Json )
  @strongly_expire
  @grab_user_id
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
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if notebook is None:
      note = None
    else:
      note = self.__database.select_one( Note, notebook.sql_load_note_by_title( note_title ) )

    return dict(
      note = note,
    )

  @expose( view = Json )
  @strongly_expire
  @grab_user_id
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
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if notebook is None:
      note = None
    else:
      note = self.__database.select_one( Note, notebook.sql_load_note_by_title( note_title ) )

    return dict(
      note_id = note and note.object_id or None,
    )

  @expose( view = Json )
  @strongly_expire
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def load_note_revisions( self, notebook_id, note_id, user_id = None ):
    """
    Return the full list of revision timestamps for this note in chronological order.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_id: unicode
    @param note_id: id of note in question
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'revisions': revisionslist or None }
    @raise Access_error: the current user doesn't have access to the given notebook or note
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    note = self.__database.load( Note, note_id )

    if note:
      if note.notebook_id != notebook_id:
        raise Access_error()
      revisions = self.__database.select_many( unicode, note.sql_load_revisions() )
    else:
      revisions = None

    return dict(
      revisions = revisions,
    )

  @expose( view = Json )
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    contents = Valid_string( min = 1, max = 25000, escape_html = False ),
    startup = Valid_bool(),
    previous_revision = Valid_revision( none_okay = True ),
    user_id = Valid_id( none_okay = True ),
  )
  def save_note( self, notebook_id, note_id, contents, startup, previous_revision, user_id ):
    """
    Save a new revision of the given note. This function will work both for creating a new note and
    for updating an existing note. If the note exists and the given contents are identical to the
    existing contents for the given previous_revision, then no saving takes place and a new_revision
    of None is returned. Otherwise this method returns the timestamp of the new revision.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_id: unicode
    @param note_id: id of note to save
    @type contents: unicode
    @param contents: new textual contents of the note, including its title
    @type startup: bool
    @param startup: whether the note should be displayed on startup
    @type previous_revision: unicode or NoneType
    @param previous_revision: previous known revision timestamp of the provided note, or None if
      the note is new
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: {
      'new_revision': new revision of saved note, or None if nothing was saved,
      'previous_revision': revision immediately before new_revision, or None if the note is new
      'storage_bytes': current storage usage by user,
    }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id, read_write = True ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if not notebook:
      raise Access_error()

    note = self.__database.load( Note, note_id )

    # check whether the provided note contents have been changed since the previous revision
    def update_note( current_notebook, old_note, startup ):
      # the note hasn't been changed, so bail without updating it
      if contents == old_note.contents and startup == old_note.startup:
        new_revision = None
      # the note has changed, so update it
      else:
        note.contents = contents
        note.startup = startup
        if startup:
          if note.rank is None:
            note.rank = self.__database.select_one( float, notebook.sql_highest_rank() ) + 1
        else:
          note.rank = None

        new_revision = note.revision

      return new_revision

    # if the note is already in the given notebook, load it and update it
    if note and note.notebook_id == notebook.object_id:
      old_note = self.__database.load( Note, note_id, previous_revision )

      previous_revision = note.revision
      new_revision = update_note( notebook, old_note, startup )

    # the note is not already in the given notebook, so look for it in the trash
    elif note and notebook.trash_id and note.notebook_id == notebook.trash_id:
      old_note = self.__database.load( Note, note_id, previous_revision )

      # undelete the note, putting it back in the given notebook
      previous_revision = note.revision
      note.notebook_id = notebook.object_id
      note.deleted_from_id = None

      new_revision = update_note( notebook, old_note, startup )
    # otherwise, create a new note
    else:
      if startup:
        rank = self.__database.select_one( float, notebook.sql_highest_rank() ) + 1
      else:
        rank = None
  
      previous_revision = None
      note = Note.create( note_id, contents, notebook_id = notebook.object_id, startup = startup, rank = rank )
      new_revision = note.revision

    if new_revision:
      self.__database.save( note, commit = False )
      user = self.__users.update_storage( user_id, commit = False )
      self.__database.commit()
    else:
      user = None

    return dict(
      new_revision = new_revision,
      previous_revision = previous_revision,
      storage_bytes = user and user.storage_bytes or 0,
    )

  @expose( view = Json )
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def delete_note( self, notebook_id, note_id, user_id ):
    """
    Delete the given note from its notebook and move it to the notebook's trash. The note is added
    as a startup note within the trash. If the given notebook is the trash and the given note is
    already there, then it is deleted from the trash forever.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_id: unicode
    @param note_id: id of note to delete
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'storage_bytes': current storage usage by user }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id, read_write = True ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if not notebook:
      raise Access_error()

    note = self.__database.load( Note, note_id )

    if note and note.notebook_id == notebook_id:
      if notebook.trash_id:
        note.deleted_from_id = notebook_id
        note.notebook_id = notebook.trash_id
        note.startup = True
      else:
        note.notebook_id = None

      self.__database.save( note, commit = False )
      user = self.__users.update_storage( user_id, commit = False )
      self.__database.commit()

      return dict( storage_bytes = user.storage_bytes )
    else:
      return dict( storage_bytes = 0 )

  @expose( view = Json )
  @grab_user_id
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
    @return: { 'storage_bytes': current storage usage by user }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id, read_write = True ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if not notebook:
      raise Access_error()

    note = self.__database.load( Note, note_id )

    if note and notebook.trash_id:
      # if the note isn't deleted, and it's already in this notebook, just return
      if note.deleted_from_id is None and note.notebook_id == notebook_id:
        return dict( storage_bytes = 0 )

      # if the note was deleted from a different notebook than the notebook given, raise
      if note.deleted_from_id != notebook_id:
        raise Access_error()

      note.notebook_id = note.deleted_from_id
      note.deleted_from_id = None
      note.startup = True

      self.__database.save( note, commit = False )
      user = self.__users.update_storage( user_id, commit = False )
      self.__database.commit()

      return dict( storage_bytes = user.storage_bytes )
    else:
      return dict( storage_bytes = 0 )

  @expose( view = Json )
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def delete_all_notes( self, notebook_id, user_id ):
    """
    Delete all notes from the given notebook and move them to the notebook's trash (if any). The
    notes are added as startup notes within the trash. If the given notebook is the trash, then
    all notes in the trash are deleted forever.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'storage_bytes': current storage usage by user }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id, read_write = True ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if not notebook:
      raise Access_error()

    notes = self.__database.select_many( Note, notebook.sql_load_notes() )

    for note in notes:
      if notebook.trash_id:
        note.deleted_from_id = notebook_id
        note.notebook_id = notebook.trash_id
        note.startup = True
      else:
        note.notebook_id = None
      self.__database.save( note, commit = False )

    user = self.__users.update_storage( user_id, commit = False )
    self.__database.commit()

    return dict(
      storage_bytes = user.storage_bytes,
    )

  @expose( view = Json )
  @strongly_expire
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    search_text = Valid_string( min = 0, max = 100 ),
    user_id = Valid_id( none_okay = True ),
  )
  def search( self, notebook_id, search_text, user_id ):
    """
    Search the notes within a particular notebook for the given search text. Note that the search
    is case-insensitive, and all HTML tags are ignored. The matching notes are returned with title
    matches first, followed by all other matches.

    @type notebook_id: unicode
    @param notebook_id: id of notebook to search
    @type search_text: unicode
    @param search_text: search term
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'notes': [ matching notes ] }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if not notebook:
      raise Access_error()

    search_text = search_text.lower()
    if len( search_text ) == 0:
      return dict( notes = [] )

    title_matches = []
    content_matches = []
    nuker = Html_nuker()

    notes = self.__database.select_many( Note, notebook.sql_search_notes( search_text ) )

    # further narrow the search results by making sure notes still match after all HTML tags are
    # stripped out
    for note in notes:
      if search_text in nuker.nuke( note.title ).lower():
        title_matches.append( note )
      elif search_text in nuker.nuke( note.contents ).lower():
        content_matches.append( note )

    return dict(
      notes = title_matches + content_matches,
    )

  @expose( view = Json )
  @strongly_expire
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def all_notes( self, notebook_id, user_id ):
    """
    Return ids and titles of all notes in this notebook, sorted by reverse chronological order.

    @type notebook_id: unicode
    @param notebook_id: id of notebook to pull notes from
    @type user_id: unicode
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'notes': [ ( noteid, notetitle ) ] }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if not notebook:
      raise Access_error()

    notes = self.__database.select_many( Note, notebook.sql_load_notes() )

    return dict(
      notes = [ ( note.object_id, note.title ) for note in notes ]
    )

  @expose( view = Html_file )
  @strongly_expire
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def download_html( self, notebook_id, user_id ):
    """
    Download the entire contents of the given notebook as a stand-alone HTML page (no JavaScript).

    @type notebook_id: unicode
    @param notebook_id: id of notebook to download
    @type user_id: unicode
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: unicode
    @return: rendered HTML page
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if not notebook:
      raise Access_error()

    startup_notes = self.__database.select_many( Note, notebook.sql_load_startup_notes() )
    other_notes = self.__database.select_many( Note, notebook.sql_load_non_startup_notes() )

    return dict(
      notebook_name = notebook.name,
      notes = startup_notes + other_notes,
    )
