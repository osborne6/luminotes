import re
import cgi
import cherrypy
from cherrypy.filters import basefilter
from datetime import datetime
from Expose import expose
from Validate import validate, Valid_string, Validation_error, Valid_bool
from Database import Valid_id, Valid_revision
from Users import grab_user_id
from Expire import strongly_expire
from Html_nuker import Html_nuker
from model.Notebook import Notebook
from model.Note import Note
from model.Invite import Invite
from model.User import User
from model.User_revision import User_revision
from view.Main_page import Main_page
from view.Json import Json
from view.Html_file import Html_file
from view.Upload_page import Upload_page


class Access_error( Exception ):
  def __init__( self, message = None ):
    if message is None:
      message = u"Sorry, you don't have access to do that. Please make sure you're logged in as the correct user."

    Exception.__init__( self, message )
    self.__message = message

  def to_dict( self ):
    return dict(
      error = self.__message
    )


class Upload_error( Exception ):
  def __init__( self, message = None ):
    if message is None:
      message = u"An error occurred when uploading the file."

    Exception.__init__( self, message )
    self.__message = message

  def to_dict( self ):
    return dict(
      error = self.__message
    )


class File_upload_filter( basefilter.BaseFilter ):
  def before_request_body( self ):
    if cherrypy.request.path != "/notebooks/upload_file":
      return

    if cherrypy.request.method != "POST":
      raise Upload_error()

    # tell CherryPy not to parse the POST data itself for this URL
    cherrypy.request.processRequestBody = False


class Notebooks( object ):
  WHITESPACE_PATTERN = re.compile( u"\s+" )
  _cpFilterList = [ File_upload_filter() ]

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
  @strongly_expire
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    parent_id = Valid_id(),
    revision = Valid_revision(),
    rename = Valid_bool(),
    deleted_id = Valid_id(),
    preview = Valid_string(),
    user_id = Valid_id( none_okay = True ),
  )
  def default( self, notebook_id, note_id = None, parent_id = None, revision = None, rename = False,
               deleted_id = None, preview = None, user_id = None ):
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
    @type rename: bool or NoneType
    @param rename: whether this is a new notebook and should be renamed (optional, defaults to False)
    @type deleted_id: unicode or NoneType
    @param deleted_id: id of the notebook that was just deleted, if any (optional)
    @type preview: unicode
    @param preview: type of access with which to preview this notebook, either "collaborator",
                    "viewer", "owner", or "default" (optional, defaults to "default"). access must
                    be equal to or lower than user's own access level to this notebook
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: unicode
    @return: rendered HTML page
    """
    result = self.__users.current( user_id )

    if preview == u"collaborator":
      read_write = True
      owner = False
      result[ u"notebooks" ] = [
        notebook for notebook in result[ "notebooks" ] if notebook.object_id == notebook_id
      ]
      result[ u"notebooks" ][ 0 ].owner = False
    elif preview == u"viewer":
      read_write = False
      owner = False
      result[ u"notebooks" ] = [
        notebook for notebook in result[ "notebooks" ] if notebook.object_id == notebook_id
      ]
      result[ u"notebooks" ][ 0 ].read_write = False
      result[ u"notebooks" ][ 0 ].owner = False
    elif preview in ( u"owner", u"default", None ):
      read_write = True
      owner = True
    else:
      raise Access_error()

    result.update( self.contents( notebook_id, note_id, revision, read_write, owner, user_id ) )
    result[ "parent_id" ] = parent_id
    if revision:
      result[ "note_read_write" ] = False

    # if the user doesn't have any storage bytes yet, they're a new user, so see what type of
    # conversion this is (demo or signup)
    if result[ "user" ].storage_bytes == 0:
      if u"this is a demo" in [ note.title for note in result[ "startup_notes" ] ]:
        result[ "conversion" ] = u"demo"
      else:
        result[ "conversion" ] = u"signup"
    result[ "rename" ] = rename
    result[ "deleted_id" ] = deleted_id

    return result

  def contents( self, notebook_id, note_id = None, revision = None, read_write = True, owner = True, user_id = None ):
    """
    Return the startup notes for the given notebook. Optionally include a single requested note as
    well.

    @type notebook_id: unicode
    @param notebook_id: id of notebook to return
    @type note_id: unicode or NoneType
    @param note_id: id of single note in this notebook to return (optional)
    @type revision: unicode or NoneType
    @param revision: revision timestamp of the provided note (optional)
    @type read_write: bool or NoneType
    @param read_write: whether the notebook should be returned as read-write (optional, defaults to True)
    @type owner: bool or NoneType
    @param owner: whether the notebook should be returned as owner-level access (optional, defaults to True)
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: dict
    @return: {
      'notebook': notebook,
      'startup_notes': notelist,
      'total_notes_count': notecount,
      'notes': notelist,
    }
    @raise Access_error: the current user doesn't have access to the given notebook or note
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if notebook is None:
      raise Access_error()

    if read_write is False:
      notebook.read_write = False
    elif not self.__users.check_access( user_id, notebook_id, read_write = True ):
      notebook.read_write = False

    if owner is False:
      notebook.owner = False
    elif not self.__users.check_access( user_id, notebook_id, owner = True ):
      notebook.owner = False

    if note_id:
      note = self.__database.load( Note, note_id, revision )
      if note and note.notebook_id != notebook_id:
        if note.notebook_id == notebook.trash_id:
          note = None
        else:
          raise Access_error()
    else:
      note = None

    startup_notes = self.__database.select_many( Note, notebook.sql_load_startup_notes() )
    total_notes_count = self.__database.select_one( int, notebook.sql_count_notes() )

    if self.__users.check_access( user_id, notebook_id, owner = True ):
      invites = self.__database.select_many( Invite, Invite.sql_load_notebook_invites( notebook_id ) )
    else:
      invites = []

    return dict(
      notebook = notebook,
      startup_notes = startup_notes,
      total_notes_count = total_notes_count,
      notes = note and [ note ] or [],
      invites = invites or [],
    )

  @expose( view = Json )
  @strongly_expire
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    revision = Valid_revision(),
    summarize = Valid_bool(),
    user_id = Valid_id( none_okay = True ),
  )
  def load_note( self, notebook_id, note_id, revision = None, summarize = False, user_id = None ):
    """
    Return the information on a particular note by its id.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_id: unicode
    @param note_id: id of note to return
    @type revision: unicode or NoneType
    @param revision: revision timestamp of the note (optional)
    @type summarize: bool or NoneType
    @param summarize: True to return a summary of the note's contents, False to return full text
                      (optional, defaults to False)
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

    # if the note has no notebook, it has been deleted "forever"
    if note and note.notebook_id is None:
      return dict(
        note = None,
      )

    if note and note.notebook_id != notebook_id:
      notebook = self.__database.load( Notebook, notebook_id )
      if notebook and note.notebook_id == notebook.trash_id:
        if revision:
          return dict(
            note = summarize and self.summarize_note( note ) or note,
          )

        return dict(
          note = None,
          note_id_in_trash = note.object_id,
        )

      raise Access_error()

    return dict(
      note = summarize and self.summarize_note( note ) or note,
    )

  @expose( view = Json )
  @strongly_expire
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_title = Valid_string( min = 1, max = 500 ),
    summarize = Valid_bool(),
    user_id = Valid_id( none_okay = True ),
  )
  def load_note_by_title( self, notebook_id, note_title, summarize = False, user_id = None ):
    """
    Return the information on a particular note by its title.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_title: unicode
    @param note_title: title of the note to return
    @type summarize: bool or NoneType
    @param summarize: True to return a summary of the note's contents, False to return full text
                      (optional, defaults to False)
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
      note = summarize and self.summarize_note( note ) or note,
    )

  def summarize_note( self, note ):
    """
    Create a truncated note summary for the given note, and then return the note with its summary
    set.

    @type note: model.Note or NoneType
    @param note: note to summarize, or None
    @rtype: model.Note or NoneType
    @return: note with its summary member set, or None if no note was provided
    """
    MAX_SUMMARY_LENGTH = 40
    word_count = 10

    if note is None:
      return None

    if note.contents is None:
      return note

    # remove all HTML from the contents and also remove the title
    summary = Html_nuker().nuke( note.contents ).strip()
    if note.title and summary.startswith( note.title ):
      summary = summary[ len( note.title ) : ]

    # split the summary on whitespace
    words = self.WHITESPACE_PATTERN.split( summary )

    def first_words( words, word_count ):
      return u" ".join( words[ : word_count ] )

    # find a summary less than MAX_SUMMARY_LENGTH and, if possible, truncated on a word boundary
    truncated = False
    summary = first_words( words, word_count )

    while len( summary ) > MAX_SUMMARY_LENGTH:
      word_count -= 1
      summary = first_words( words, word_count )

      # if the first word is just ridiculously long, truncate it without finding a word boundary
      if word_count == 1:
        summary = summary[ : MAX_SUMMARY_LENGTH ]
        truncated = True
        break

    if truncated or word_count < len( words ):
      summary += " ..."

    note.summary = summary
    return note

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
    @return: { 'revisions': userrevisionlist or None }
    @raise Access_error: the current user doesn't have access to the given notebook or note
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    note = self.__database.load( Note, note_id )

    if note:
      if note and note.notebook_id is None:
        return dict(
          revisions = None,
        )

      if note.notebook_id != notebook_id:
        notebook = self.__database.load( Notebook, notebook_id )
        if notebook and note.notebook_id == notebook.trash_id:
          return dict(
            revisions = None,
          )

        raise Access_error()

      revisions = self.__database.select_many( User_revision, note.sql_load_revisions() )
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
      'new_revision': User_revision of saved note, or None if nothing was saved
      'previous_revision': User_revision immediately before new_revision, or None if the note is new
      'storage_bytes': current storage usage by user,
    }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id, read_write = True ):
      raise Access_error()

    user = self.__database.load( User, user_id )
    notebook = self.__database.load( Notebook, notebook_id )

    if not user or not notebook:
      raise Access_error()

    note = self.__database.load( Note, note_id )

    # check whether the provided note contents have been changed since the previous revision
    def update_note( current_notebook, old_note, startup, user ):
      # the note hasn't been changed, so bail without updating it
      if contents.replace( u"\n", u"" ) == old_note.contents.replace( u"\n", "" ) and startup == old_note.startup:
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
        note.user_id = user.object_id

        new_revision = User_revision( note.revision, note.user_id, user.username )

      return new_revision

    # if the note is already in the given notebook, load it and update it
    if note and note.notebook_id == notebook.object_id:
      old_note = self.__database.load( Note, note_id, previous_revision )

      previous_user = self.__database.load( User, note.user_id )
      previous_revision = User_revision( note.revision, note.user_id, previous_user and previous_user.username or None )
      new_revision = update_note( notebook, old_note, startup, user )

    # the note is not already in the given notebook, so look for it in the trash
    elif note and notebook.trash_id and note.notebook_id == notebook.trash_id:
      old_note = self.__database.load( Note, note_id, previous_revision )

      # undelete the note, putting it back in the given notebook
      previous_user = self.__database.load( User, note.user_id )
      previous_revision = User_revision( note.revision, note.user_id, previous_user and previous_user.username or None )
      note.notebook_id = notebook.object_id
      note.deleted_from_id = None

      new_revision = update_note( notebook, old_note, startup, user )
    # otherwise, create a new note
    else:
      if startup:
        rank = self.__database.select_one( float, notebook.sql_highest_rank() ) + 1
      else:
        rank = None
  
      previous_revision = None
      note = Note.create( note_id, contents, notebook_id = notebook.object_id, startup = startup, rank = rank, user_id = user_id )
      new_revision = User_revision( note.revision, note.user_id, user.username )

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
      note.user_id = user_id

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
      note.user_id = user_id

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
      note.user_id = user_id

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
    search_text = unicode,
    user_id = Valid_id( none_okay = True ),
  )
  def search( self, notebook_id, search_text, user_id ):
    """
    Search the notes within a particular notebook for the given search text. Note that the search
    is case-insensitive, and all HTML tags are ignored. Notes with title matches are generally
    ranked higher than matches that are only in the note contents. The returned notes include
    content summaries with the search terms highlighted.

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
    @raise Search_error: the provided search_text is invalid
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if not notebook:
      raise Access_error()

    MAX_SEARCH_TEXT_LENGTH = 256
    if len( search_text ) > MAX_SEARCH_TEXT_LENGTH:
      raise Validation_error( u"search_text", None, unicode, message = u"is too long" )

    if len( search_text ) == 0:
      raise Validation_error( u"search_text", None, unicode, message = u"is missing" )

    notes = self.__database.select_many( Note, notebook.sql_search_notes( search_text ) )

    return dict(
      notes = notes,
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

  @expose( view = Json )
  @grab_user_id
  @validate(
    user_id = Valid_id( none_okay = True ),
  )
  def create( self, user_id ):
    """
    Create a new notebook and give it a default name.

    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype dict
    @return { "redirect": notebookurl }
    @raise Access_error: the current user doesn't have access to create a notebook
    @raise Validation_error: one of the arguments is invalid
    """
    if user_id is None:
      raise Access_error()

    user = self.__database.load( User, user_id )
    notebook = self.__create_notebook( u"new notebook", user )

    return dict(
      redirect = u"/notebooks/%s?rename=true" % notebook.object_id,
    )

  def __create_notebook( self, name, user, commit = True ):
    # create the notebook along with a trash
    trash_id = self.__database.next_id( Notebook, commit = False )
    trash = Notebook.create( trash_id, u"trash", user_id = user.object_id )
    self.__database.save( trash, commit = False )

    notebook_id = self.__database.next_id( Notebook, commit = False )
    notebook = Notebook.create( notebook_id, name, trash_id, user_id = user.object_id )
    self.__database.save( notebook, commit = False )

    # record the fact that the user has access to their new notebook
    self.__database.execute( user.sql_save_notebook( notebook_id, read_write = True, owner = True ), commit = False )
    self.__database.execute( user.sql_save_notebook( trash_id, read_write = True, owner = True ), commit = False )

    if commit:
      self.__database.commit()

    return notebook

  @expose( view = Json )
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    name = Valid_string( min = 1, max = 100 ),
    user_id = Valid_id( none_okay = True ),
  )
  def rename( self, notebook_id, name, user_id ):
    """
    Change the name of the given notebook.

    @type notebook_id: unicode
    @param notebook_id: id of notebook to rename
    @type name: unicode
    @param name: new name of the notebook
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype dict
    @return {}
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    user = self.__database.load( User, user_id )
    if not self.__users.check_access( user_id, notebook_id, read_write = True, owner = True ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if not notebook:
      raise Access_error()

    # prevent renaming of the trash notebook to anything
    if notebook.name == u"trash":
      raise Access_error()

    # prevent just anyone from making official Luminotes notebooks
    if name.startswith( u"Luminotes" ) and not notebook.name.startswith( u"Luminotes" ):
      raise Access_error()

    # prevent renaming of another notebook to "trash"
    if name == u"trash":
      raise Access_error()

    notebook.name = name
    notebook.user_id = user_id

    self.__database.save( notebook, commit = False )
    self.__database.commit()

    return dict()

  @expose( view = Json )
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def delete( self, notebook_id, user_id ):
    """
    Delete the given notebook and redirect to a remaining read-write notebook. If there is none,
    create one.

    @type notebook_id: unicode
    @param notebook_id: id of notebook to delete
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype dict
    @return { "redirect": remainingnotebookurl }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    if user_id is None:
      raise Access_error()

    user = self.__database.load( User, user_id )

    if not self.__users.check_access( user_id, notebook_id, read_write = True, owner = True ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if not notebook:
      raise Access_error()

    # prevent deletion of a trash notebook directly
    if notebook.name == u"trash":
      raise Access_error()

    notebook.deleted = True
    notebook.user_id = user_id

    self.__database.save( notebook, commit = False )

    # redirect to a remaining undeleted read-write notebook, or if there isn't one, create an empty notebook
    remaining_notebook = self.__database.select_one( Notebook, user.sql_load_notebooks(
      parents_only = True, undeleted_only = True, read_write = True,
    ) )
    if remaining_notebook is None:
      remaining_notebook = self.__create_notebook( u"my notebook", user, commit = False )

    self.__database.commit()

    return dict(
      redirect = u"/notebooks/%s?deleted_id=%s" % ( remaining_notebook.object_id, notebook.object_id ),
    )

  @expose( view = Json )
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def delete_forever( self, notebook_id, user_id ):
    """
    Delete the given notebook permanently (by simply revoking the user's access to it).

    @type notebook_id: unicode
    @param notebook_id: id of notebook to delete
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype dict
    @return: { 'storage_bytes': current storage usage by user }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    if user_id is None:
      raise Access_error()

    user = self.__database.load( User, user_id )

    if not self.__users.check_access( user_id, notebook_id, read_write = True, owner = True ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if not notebook:
      raise Access_error()

    # prevent deletion of a trash notebook directly
    if notebook.name == u"trash":
      raise Access_error()

    self.__database.execute( user.sql_remove_notebook( notebook_id ), commit = False )
    user = self.__users.update_storage( user_id, commit = False )
    self.__database.commit()

    return dict( storage_bytes = user.storage_bytes )

  @expose( view = Json )
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def undelete( self, notebook_id, user_id ):
    """
    Undelete the given notebook and redirect to it.

    @type notebook_id: unicode
    @param notebook_id: id of notebook to undelete
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype dict
    @return { "redirect": notebookurl }
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    if user_id is None:
      raise Access_error()

    if not self.__users.check_access( user_id, notebook_id, read_write = True, owner = True ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )

    if not notebook:
      raise Access_error()

    notebook.deleted = False
    notebook.user_id = user_id

    self.__database.save( notebook, commit = False )
    self.__database.commit()

    return dict(
      redirect = u"/notebooks/%s" % notebook.object_id,
    )

  def load_recent_notes( self, notebook_id, start = 0, count = 10, user_id = None ):
    """
    Provide the information necessary to display the page for a particular notebook's most recent
    notes.

    @type notebook_id: unicode
    @param notebook_id: id of the notebook to display
    @type start: unicode or NoneType
    @param start: index of recent note to start with (defaults to 0, the most recent note)
    @type count: int or NoneType
    @param count: number of recent notes to display (defaults to 10 notes)
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: dict
    @return: data for Main_page() constructor
    @raise Access_error: the current user doesn't have access to the given notebook or note
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()
    
    notebook = self.__database.load( Notebook, notebook_id )

    if notebook is None:
      raise Access_error()

    recent_notes = self.__database.select_many( Note, notebook.sql_load_recent_notes( start, count ) )

    result = self.__users.current( user_id )
    result.update( self.contents( notebook_id, user_id = user_id ) )
    result[ "notes" ] = recent_notes
    result[ "start" ] = start
    result[ "count" ] = count

    return result

  @expose( view = Upload_page )
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
  )
  def upload_page( self, notebook_id, note_id ):
    """
    Provide the information necessary to display the file upload page.

    @type notebook_id: unicode
    @param notebook_id: id of the notebook that the upload will be to
    @type note_id: unicode
    @param note_id: id of the note that the upload will be to
    @rtype: unicode
    @return: rendered HTML page
    """
    return dict(
      notebook_id = notebook_id,
      note_id = note_id,
    )

  @expose()
  @strongly_expire
  @grab_user_id
  @validate(
    user_id = Valid_id( none_okay = True ),
  )
  def upload_file( self, user_id ):
    """
    Upload a file from the client for attachment to a particular note.

    @type notebook_id: unicode
    @param notebook_id: id of the notebook that the upload is to
    @type note_id: unicode
    @param note_id: id of the note that the upload is to
    @raise Access_error: the current user doesn't have access to the given notebook or note
    @rtype: unicode
    @return: rendered HTML page
    """
    cherrypy.server.max_request_body_size = 0 # remove file size limit of 100 MB
    cherrypy.response.timeout = 3600    # increase upload timeout to one hour (default is 5 min)
    cherrypy.server.socket_timeout = 60 # increase socket timeout to one minute (default is 10 sec)
    # TODO: increase to 8k
    CHUNK_SIZE = 1#8 * 1024 # 8 Kb

    headers = {}
    for key, val in cherrypy.request.headers.iteritems():
      headers[ key.lower() ] = val

    try:
      file_size = int( headers.get( "content-length", 0 ) )
    except ValueError:
      raise Upload_error()
    if file_size <= 0:
      raise Upload_error()

    parsed_form = cgi.FieldStorage( fp = cherrypy.request.rfile, headers = headers, environ = { "REQUEST_METHOD": "POST" }, keep_blank_values = 1)
    upload = parsed_form[ u"file" ]
    notebook_id = parsed_form.getvalue( u"notebook_id" )
    note_id = parsed_form.getvalue( u"note_id" )
    filename = upload.filename.strip()

    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    def process_upload():
      """
      Process the file upload while streaming a progress meter as it uploads.
      """
      progress_bytes = 0
      fraction_reported = 0.0
      progress_width_em = 20
      tick_increment = 0.01
      progress_bar = u'<img src="/static/images/tick.png" style="width: %sem; height: 1em;" id="progress_bar" />' % \
        ( progress_width_em * tick_increment )

      yield \
        u"""
        <html>
        <head>
          <link href="/static/css/upload.css" type="text/css" rel="stylesheet" />
          <script type="text/javascript" src="/static/js/MochiKit.js"></script>
          <meta content="text/html; charset=UTF-8" http_equiv="content-type" />
        </head>
        <body>
        """

      if not filename:
        yield \
          u"""
          <div class="field_label">upload error: </div>
          Please check that the filename is valid.
          """
        return

      base_filename = filename.split( u"/" )[ -1 ].split( u"\\" )[ -1 ]
      yield \
        u"""
        <div class="field_label">uploading %s: </div>
        <div id="progress_border">
        %s
        </div>
        <script type="text/javascript">
        function tick( fraction ) {
          setElementDimensions(
            "progress_bar",
            { "w": %s * fraction }, "em"
          );
        }
        </script>
        """ % ( cgi.escape( base_filename ), progress_bar, progress_width_em )

      import time
      while True:
        chunk = upload.file.read( CHUNK_SIZE )
        if not chunk: break
        progress_bytes += len( chunk )
        fraction_done = float( progress_bytes ) / float( file_size )

        if fraction_done > fraction_reported + tick_increment:
          yield '<script type="text/javascript">tick(%s)</script>;' % fraction_reported
          fraction_reported += tick_increment
          time.sleep(0.025) # TODO: removeme

        # TODO: write to the database

      if fraction_reported == 0:
        yield "An error occurred when uploading the file."
        return

      # the file finished uploading, so fill out the progress meter to 100%
      if fraction_reported < 1.0:
        yield '<script type="text/javascript">tick(1.0)</script>;'

      yield \
        u"""
        </script>
        </body>
        </html>
        """

      upload.file.close()
      cherrypy.request.rfile.close()

    return process_upload()
