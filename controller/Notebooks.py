import re
import cgi
import cherrypy
from datetime import datetime
from Expose import expose
from Validate import validate, Valid_string, Validation_error, Valid_bool, Valid_int
from Database import Valid_id, Valid_revision, end_transaction
from Users import grab_user_id, Access_error
from Expire import strongly_expire, weakly_expire
from Html_nuker import Html_nuker
from Html_differ import Html_differ
from Files import Upload_file
from model.Notebook import Notebook
from model.Note import Note
from model.Invite import Invite
from model.User import User
from model.User_revision import User_revision
from model.File import File
from view.Main_page import Main_page
from view.Json import Json
from view.Html_file import Html_file
from view.Note_tree_area import Note_tree_area
from view.Notebook_rss import Notebook_rss
from view.Updates_rss import Updates_rss
from view.Update_link_page import Update_link_page


class Import_error( Exception ):
  def __init__( self, message = None ):
    if message is None:
      message = u"An error occurred when trying to import your file. Please try a different file, or contact support for help."

    Exception.__init__( self, message )
    self.__message = message

  def to_dict( self ):
    return dict(
      error = self.__message
    )


class Notebooks( object ):
  WHITESPACE_PATTERN = re.compile( u"\s+" )
  LINK_PATTERN = re.compile( u'<a\s+((?:[^>]+\s)?href="([^"]+)"(?:\s+target="([^"]*)")?[^>]*)>(<img [^>]+>)?([^<]*)</a>', re.IGNORECASE )
  FILE_PATTERN = re.compile( u'/files/' )
  NEW_FILE_PATTERN = re.compile( u'/files/new' )

  """
  Controller for dealing with notebooks and their notes, corresponding to the "/notebooks" URL.
  """
  def __init__( self, database, users, files, https_url ):
    """
    Create a new Notebooks object.

    @type database: controller.Database
    @param database: database that notebooks are stored in
    @type users: controller.Users
    @param users: controller for all users, used here for updating storage utilization
    @type files: controller.Files
    @param files: controller for all uploaded files, used here for deleting files that are no longer
                  referenced within saved notes
    @type https_url: unicode
    @param https_url: base URL to use for SSL http requests, or an empty string
    @return: newly constructed Notebooks
    """
    self.__database = database
    self.__users = users
    self.__files = files
    self.__https_url = https_url

  @expose( view = Main_page, rss = Notebook_rss )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    parent_id = Valid_id(),
    revision = Valid_revision(),
    previous_revision = Valid_revision( none_okay = True ),
    rename = Valid_bool(),
    deleted_id = Valid_id(),
    preview = Valid_string(),
    user_id = Valid_id( none_okay = True ),
  )
  def default( self, notebook_id, note_id = None, parent_id = None, revision = None,
               previous_revision = None, rename = False, deleted_id = None, preview = None,
               user_id = None ):
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
    @type previous_revision: unicode or NoneType
    @param previous_revision: older revision timestamp to diff with the given revision (optional)
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
      if len( result[ u"notebooks" ] ) == 0:
        raise Access_error()
      result[ u"notebooks" ][ 0 ].owner = False
    elif preview == u"viewer":
      read_write = False
      owner = False
      result[ u"notebooks" ] = [
        notebook for notebook in result[ "notebooks" ] if notebook.object_id == notebook_id
      ]
      if len( result[ u"notebooks" ] ) == 0:
        raise Access_error()
      result[ u"notebooks" ][ 0 ].read_write = False
      result[ u"notebooks" ][ 0 ].owner = False
    elif preview in ( u"owner", u"default", None ):
      read_write = True
      owner = True
    else:
      raise Access_error()

    result.update( self.contents( notebook_id, note_id, revision, previous_revision, read_write, owner, user_id ) )
    result[ "parent_id" ] = parent_id
    if revision:
      result[ "note_read_write" ] = False

    notebook = self.__database.load( Notebook, notebook_id )
    if not notebook:
      raise Access_error()
    if notebook.name != u"Luminotes":
      result[ "recent_notes" ] = self.__database.select_many( Note, notebook.sql_load_notes( start = 0, count = 10 ) )

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

  def contents( self, notebook_id, note_id = None, revision = None, previous_revision = None,
                read_write = True, owner = True, user_id = None ):
    """
    Return the startup notes for the given notebook. Optionally include a single requested note as
    well.

    @type notebook_id: unicode
    @param notebook_id: id of notebook to return
    @type note_id: unicode or NoneType
    @param note_id: id of single note in this notebook to return (optional)
    @type revision: unicode or NoneType
    @param revision: revision timestamp of the provided note (optional)
    @type previous_revision: unicode or NoneType
    @param previous_revision: older revision timestamp to diff with the given revision (optional)
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
      'invites': invitelist
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

      # if two revisions were provided, then make the returned note's contents into a diff
      if note and revision and previous_revision:
        previous_note = self.__database.load( Note, note_id, previous_revision )
        if previous_note and previous_note.contents:
          note.replace_contents( Html_differ().diff( previous_note.contents, note.contents ) )
    else:
      note = None

    startup_notes = self.__database.select_many( Note, notebook.sql_load_startup_notes() )
    total_notes_count = self.__database.select_one( int, notebook.sql_count_notes(), use_cache = True )

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

  @expose( view = None, rss = Updates_rss )
  @strongly_expire
  @end_transaction
  @validate(
    notebook_id = Valid_id(),
    notebook_name = Valid_string(),
  )
  def updates( self, notebook_id, notebook_name ):
    """
    Provide the information necessary to display an updated notes RSS feed for the given notebook.
    This method does not require any sort of login.

    @type notebook_id: unicode
    @param notebook_id: id of the notebook to provide updates for
    @type notebook_name: unicode
    @param notebook_name: name of the notebook to include in the RSS feed
    @rtype: unicode
    @return: rendered RSS feed
    """
    notebook = self.__database.load( Notebook, notebook_id )
    if not notebook:
      return dict(
        recent_notes = [],
        notebook_id = notebook_id,
        notebook_name = notebook_name,
        https_url = self.__https_url,
      )

    recent_notes = self.__database.select_many( Note, notebook.sql_load_notes( start = 0, count = 10 ) )

    return dict(
      recent_notes = [ ( note.object_id, note.revision ) for note in recent_notes ],
      notebook_id = notebook_id,
      notebook_name = notebook_name,
      https_url = self.__https_url,
    )

  @expose( view = Update_link_page )
  @strongly_expire
  @end_transaction
  @validate(
    notebook_id = Valid_id(),
    notebook_name = Valid_string(),
    note_id = Valid_id(),
    revision = Valid_revision(), 
  )
  def get_update_link( self, notebook_id, notebook_name, note_id, revision ):
    """
    Provide the information necessary to display a link to an updated note. This method does not
    require any sort of login.

    @type notebook_id: unicode
    @param notebook_id: id of the notebook the note is in
    @type notebook_name: unicode
    @param notebook_name: name of the notebook
    @type note_id: unicode
    @param note_id: id of the note to link to
    @type revision: unicode
    @param revision: ignored; present so RSS feed readers distinguish between different revisions
    @rtype: unicode
    @return: rendered HTML page
    """
    return dict(
      notebook_id = notebook_id,
      notebook_name = notebook_name,
      note_id = note_id,
      https_url = self.__https_url,
    )

  @expose( view = Json )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    revision = Valid_revision(),
    previous_revision = Valid_revision( none_okay = True ),
    summarize = Valid_bool(),
    user_id = Valid_id( none_okay = True ),
  )
  def load_note( self, notebook_id, note_id, revision = None, previous_revision = None, summarize = False, user_id = None ):
    """
    Return the information on a particular note by its id.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_id: unicode
    @param note_id: id of note to return
    @type revision: unicode or NoneType
    @param revision: revision timestamp of the note (optional)
    @type previous_revision: unicode or NoneType
    @param previous_revision: older revision timestamp to diff with the given revision (optional)
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

    if note and revision and previous_revision:
      previous_note = self.__database.load( Note, note_id, previous_revision )
      if previous_note and previous_note.contents:
        note.replace_contents( Html_differ().diff( previous_note.contents, note.contents ) )

    return dict(
      note = summarize and self.summarize_note( note ) or note,
    )

  @expose( view = Json )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_title = Valid_string( min = 1, max = 500 ),
    summarize = Valid_bool(),
    user_id = Valid_id( none_okay = True ),
  )
  def load_note_by_title( self, notebook_id, note_title, summarize = False, user_id = None ):
    """
    Return the information on a particular note by its title. The lookup by title is performed
    case-insensitively.

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
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_title = Valid_string( min = 1, max = 500 ),
    user_id = Valid_id( none_okay = True ),
  )
  def lookup_note_id( self, notebook_id, note_title, user_id ):
    """
    Return a note's id by looking up its title. The lookup by title is performed
    case-insensitively.

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
  @end_transaction
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
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def load_note_links( self, notebook_id, note_id, user_id = None ):
    """
    Return a list of HTTP links found within the contents of the given note.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_id: unicode
    @param note_id: id of note in question
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: { 'tree_html': html_fragment }
    @raise Access_error: the current user doesn't have access to the given notebook or note
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    notebook = self.__database.load( Notebook, notebook_id )
    if not notebook:
      raise Access_error()

    note = self.__database.load( Note, note_id )
    if note is None or note.notebook_id not in ( notebook_id, notebook.trash_id ):
      raise Access_error()

    items = []

    for match in self.LINK_PATTERN.finditer( note.contents ):
      ( attributes, href, target, embedded_image, title ) = match.groups()

      # if it has a link target, it's a link to an external web site
      if target:
        items.append( Note_tree_area.make_item( title, attributes, u"note_tree_external_link" ) )
        continue

      # if it has '/files/' in its path, it's an uploaded file link
      if self.FILE_PATTERN.search( href ):
        if not self.NEW_FILE_PATTERN.search( href ): # ignore files that haven't been uploaded yet
          if embedded_image:
            title = u"embedded image"
          items.append( Note_tree_area.make_item( title, attributes, u"note_tree_file_link", target = u"_new" ) )
        continue

      # if it has a note_id, load that child note and see whether it has any children of its own
      child_note_ids = cgi.parse_qs( href.split( '?' )[ -1 ] ).get( u"note_id" )

      if child_note_ids:
        child_note_id = child_note_ids[ 0 ]
        child_note = self.__database.load( Note, child_note_id )
        if child_note and child_note.contents and self.LINK_PATTERN.search( child_note.contents ):
          items.append( Note_tree_area.make_item( title, attributes, u"note_tree_link", has_children = True ) )
          continue

      # otherwise, it's childless
      items.append( Note_tree_area.make_item( title, attributes, u"note_tree_link", has_children = False ) )

    return dict(
      tree_html = unicode( Note_tree_area.make_tree( items ) ),
    )

  @expose( view = Json )
  @end_transaction
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
            note.rank = self.__database.select_one( float, notebook.sql_highest_note_rank() ) + 1
        else:
          note.rank = None
        note.user_id = user.object_id

        new_revision = User_revision( note.revision, note.user_id, user.username )

        self.__files.purge_unused( note )

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
        rank = self.__database.select_one( float, notebook.sql_highest_note_rank() ) + 1
      else:
        rank = None
  
      previous_revision = None
      note = Note.create( note_id, contents, notebook_id = notebook.object_id, startup = startup, rank = rank, user_id = user_id )
      new_revision = User_revision( note.revision, note.user_id, user.username )

    if new_revision:
      self.__database.save( note, commit = False )
      user = self.__users.update_storage( user_id, commit = False )
      self.__database.uncache_command( notebook.sql_count_notes() ) # cached note count is now invalid
      self.__database.commit()
      user.group_storage_bytes = self.__users.calculate_group_storage( user )
    else:
      user = None

    return dict(
      new_revision = new_revision,
      previous_revision = previous_revision,
      storage_bytes = user and user.storage_bytes or 0,
    )

  @expose( view = Json )
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    revision = Valid_revision(),
    user_id = Valid_id( none_okay = True ),
  )
  def revert_note( self, notebook_id, note_id, revision, user_id ):
    """
    Revert the contents of a note to that of an earlier revision, thereby creating a new revision.
    The timestamp of the new revision is returned.

    @type notebook_id: unicode
    @param notebook_id: id of notebook the note is in
    @type note_id: unicode
    @param note_id: id of note to revert
    @type revision: unicode or NoneType
    @param revision: revision timestamp to revert to for the provided note
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any), determined by @grab_user_id
    @rtype: json dict
    @return: {
      'new_revision': User_revision of the reverted note
      'previous_revision': User_revision immediately before new_revision
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

    if not note:
      raise Access_error()

    # check whether the provided note contents have been changed since the previous revision
    def update_note( current_notebook, old_note, user ):
      # if the revision to revert to is already the newest revision, bail without updating the note
      if old_note.revision == note.revision:
        new_revision = None
      # otherwise, revert the note's contents to that of the older revision
      else:
        note.contents = old_note.contents
        note.user_id = user.object_id
        new_revision = User_revision( note.revision, note.user_id, user.username )

        self.__files.purge_unused( note )

      return new_revision

    previous_user = self.__database.load( User, note.user_id )
    previous_revision = User_revision( note.revision, note.user_id, previous_user and previous_user.username or None )

    # if the note is already in the given notebook, load it and revert it
    if note and note.notebook_id == notebook.object_id:
      old_note = self.__database.load( Note, note_id, revision )
      new_revision = update_note( notebook, old_note, user )

    # the note is not already in the given notebook, so look for it in the trash
    elif note and notebook.trash_id and note.notebook_id == notebook.trash_id:
      old_note = self.__database.load( Note, note_id, revision )

      # undelete the note, putting it back in the given notebook
      note.notebook_id = notebook.object_id
      note.deleted_from_id = None

      new_revision = update_note( notebook, old_note, user )
    # otherwise, the note doesn't exist
    else:
      raise Access_error()

    if new_revision:
      self.__database.save( note, commit = False )
      user = self.__users.update_storage( user_id, commit = False )
      self.__database.commit()
      user.group_storage_bytes = self.__users.calculate_group_storage( user )
    else:
      user = None

    return dict(
      new_revision = new_revision,
      previous_revision = previous_revision,
      storage_bytes = user and user.storage_bytes or 0,
      contents = note.contents,
    )

  @expose( view = Json )
  @end_transaction
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
        self.__files.purge_unused( note, purge_all_links = True )
        note.notebook_id = None
      note.user_id = user_id

      self.__database.save( note, commit = False )
      user = self.__users.update_storage( user_id, commit = False )
      self.__database.uncache_command( notebook.sql_count_notes() ) # cached note count is now invalid
      self.__database.commit()
      user.group_storage_bytes = self.__users.calculate_group_storage( user )

      return dict( storage_bytes = user.storage_bytes )
    else:
      return dict( storage_bytes = 0 )

  @expose( view = Json )
  @end_transaction
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
      self.__database.uncache_command( notebook.sql_count_notes() ) # cached note count is now invalid
      self.__database.commit()
      user.group_storage_bytes = self.__users.calculate_group_storage( user )

      return dict( storage_bytes = user.storage_bytes )
    else:
      return dict( storage_bytes = 0 )

  @expose( view = Json )
  @end_transaction
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
        self.__files.purge_unused( note, purge_all_links = True )
        note.notebook_id = None
      note.user_id = user_id

      self.__database.save( note, commit = False )

    user = self.__users.update_storage( user_id, commit = False )
    self.__database.uncache_command( notebook.sql_count_notes() ) # cached note count is now invalid
    self.__database.commit()
    user.group_storage_bytes = self.__users.calculate_group_storage( user )

    return dict(
      storage_bytes = user.storage_bytes,
    )

  @expose( view = Json )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    search_text = unicode,
    user_id = Valid_id( none_okay = True ),
  )
  def search_titles( self, notebook_id, search_text, user_id ):
    """
    Search the note titles within the given notebook for the given search text, and return matching
    notes. The search is case-insensitive. The returned notes include title summaries with the
    search term highlighted and are ordered by descending revision timestamp.

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

    MAX_SEARCH_TEXT_LENGTH = 256
    if len( search_text ) > MAX_SEARCH_TEXT_LENGTH:
      raise Validation_error( u"search_text", None, unicode, message = u"is too long" )

    if len( search_text ) == 0:
      raise Validation_error( u"search_text", None, unicode, message = u"is missing" )

    notes = self.__database.select_many( Note, Notebook.sql_search_titles( notebook_id, search_text ) )

    for note in notes:
      # do a case-insensitive replace to wrap the search term with bold
      search_text_pattern = re.compile( u"(%s)" % re.escape( search_text ), re.I )
      note.summary = search_text_pattern.sub( r"<b>\1</b>", note.summary )

    return dict(
      notes = notes,
    )

  @expose( view = Json )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    search_text = unicode,
    user_id = Valid_id( none_okay = True ),
  )
  def search( self, notebook_id, search_text, user_id ):
    """
    Search the notes within all notebooks that the user has access to for the given search text.
    Note that the search is case-insensitive, and all HTML tags are ignored. Notes with title
    matches are generally ranked higher than matches that are only in the note contents. The
    returned notes include content summaries with the search terms highlighted.

    @type notebook_id: unicode
    @param notebook_id: id of notebook to show first in search results
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

    # if the anonymous user has access to the given notebook, then run the search as the anonymous
    # user instead of the given user id
    if self.__users.check_access( user_id = None, notebook_id = notebook_id ) is True:
      anonymous = self.__database.select_one( User, User.sql_load_by_username( u"anonymous" ), use_cache = True )
      user_id = anonymous.object_id

    MAX_SEARCH_TEXT_LENGTH = 256
    if len( search_text ) > MAX_SEARCH_TEXT_LENGTH:
      raise Validation_error( u"search_text", None, unicode, message = u"is too long" )

    if len( search_text ) == 0:
      raise Validation_error( u"search_text", None, unicode, message = u"is missing" )

    notes = self.__database.select_many( Note, Notebook.sql_search_notes( user_id, notebook_id, search_text ) )

    return dict(
      notes = notes,
    )

  @expose( view = Json )
  @strongly_expire
  @end_transaction
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
  @weakly_expire
  @end_transaction
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
  @end_transaction
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
    @return { 'redirect': new_notebook_url }
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
    rank = self.__database.select_one( float, user.sql_highest_notebook_rank() ) + 1
    self.__database.execute( user.sql_save_notebook( notebook_id, read_write = True, owner = True, rank = rank ), commit = False )
    self.__database.execute( user.sql_save_notebook( trash_id, read_write = True, owner = True ), commit = False )

    if commit:
      self.__database.commit()

    return notebook

  @expose( view = Json )
  @end_transaction
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
  @end_transaction
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
    @return { 'redirect': remaining_notebook_url }
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
  @end_transaction
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
    user.group_storage_bytes = self.__users.calculate_group_storage( user )

    return dict( storage_bytes = user.storage_bytes )

  @expose( view = Json )
  @end_transaction
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
    @return { 'redirect': notebook_url }
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

  @expose( view = Json )
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def move_up( self, notebook_id, user_id ):
    """
    Reorder the user's notebooks by moving the given notebook up by one. If the notebook is already
    first, then wrap it around to be the last notebook.

    @type notebook_id: unicode
    @param notebook_id: id of notebook to move up
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype json dict
    @return {}
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    user = self.__database.load( User, user_id )
    if not user:
      raise Access_error()

    # load the notebooks to which this user has access
    notebooks = self.__database.select_many(
      Notebook,
      user.sql_load_notebooks( parents_only = True, undeleted_only = True ),
    )
    if not notebooks:
      raise Access_error()

    # find the given notebook and the one previous to it
    previous_notebook = None
    current_notebook = None

    for notebook in notebooks:
      if notebook.object_id == notebook_id:
        current_notebook = notebook
        break
      previous_notebook = notebook

    if current_notebook is None:
      raise Access_error()

    # if there is no previous notebook, then the current notebook is first. so, move it after the
    # last notebook
    if previous_notebook is None:
      last_notebook = notebooks[ -1 ]
      self.__database.execute(
        user.sql_update_notebook_rank( current_notebook.object_id, last_notebook.rank + 1 ),
        commit = False,
      )
    # otherwise, save the current and previous notebooks back to the database with swapped ranks
    else:
      self.__database.execute(
        user.sql_update_notebook_rank( current_notebook.object_id, previous_notebook.rank ),
        commit = False,
      )
      self.__database.execute(
        user.sql_update_notebook_rank( previous_notebook.object_id, current_notebook.rank ),
        commit = False,
      )

    self.__database.commit()

    return dict()

  @expose( view = Json )
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def move_down( self, notebook_id, user_id ):
    """
    Reorder the user's notebooks by moving the given notebook down by one. If the notebook is
    already last, then wrap it around to be the first notebook.

    @type notebook_id: unicode
    @param notebook_id: id of notebook to move down
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype json dict
    @return {}
    @raise Access_error: the current user doesn't have access to the given notebook
    @raise Validation_error: one of the arguments is invalid
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    user = self.__database.load( User, user_id )
    if not user:
      raise Access_error()

    # load the notebooks to which this user has access
    notebooks = self.__database.select_many(
      Notebook,
      user.sql_load_notebooks( parents_only = True, undeleted_only = True ),
    )
    if not notebooks:
      raise Access_error()

    # find the given notebook and the one after it
    current_notebook = None
    next_notebook = None

    for notebook in notebooks:
      if notebook.object_id == notebook_id:
        current_notebook = notebook
      elif current_notebook:
        next_notebook = notebook
        break

    if current_notebook is None:
      raise Access_error()

    # if there is no next notebook, then the current notebook is last. so, move it before the
    # first notebook
    if next_notebook is None:
      first_notebook = notebooks[ 0 ]
      self.__database.execute(
        user.sql_update_notebook_rank( current_notebook.object_id, first_notebook.rank - 1 ),
        commit = False,
      )
    # otherwise, save the current and next notebooks back to the database with swapped ranks
    else:
      self.__database.execute(
        user.sql_update_notebook_rank( current_notebook.object_id, next_notebook.rank ),
        commit = False,
      )
      self.__database.execute(
        user.sql_update_notebook_rank( next_notebook.object_id, current_notebook.rank ),
        commit = False,
      )

    self.__database.commit()

    return dict()

  @expose( view = Json )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    start = Valid_int( min = 0 ),
    count = Valid_int( min = 1 ),
    user_id = Valid_id( none_okay = True ),
  )
  def load_recent_updates( self, notebook_id, start, count, user_id = None ):
    """
    Provide the information necessary to display a notebook's recent updated/created notes, in
    reverse chronological order by update time.
    

    @type notebook_id: unicode
    @param notebook_id: id of the notebook containing the notes
    @type start: unicode or NoneType
    @param start: index of recent note to start with (defaults to 0, the most recent note)
    @type count: int or NoneType
    @param count: number of recent notes to display (defaults to 10 notes)
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: json dict
    @return: { 'notes': recent_notes_list }
    @raise Access_error: the current user doesn't have access to the given notebook or note
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()
    
    notebook = self.__database.load( Notebook, notebook_id )

    if notebook is None:
      raise Access_error()

    recent_notes = self.__database.select_many( Note, notebook.sql_load_notes( start = start, count = count ) )

    return dict(
      notes = recent_notes,
    )

  def recent_notes( self, notebook_id, start = 0, count = 10, user_id = None ):
    """
    Return the given notebook's recently updated notes in reverse chronological order by creation
    time.

    @type notebook_id: unicode
    @param notebook_id: id of the notebook containing the notes
    @type start: unicode or NoneType
    @param start: index of recent note to start with (defaults to 0, the most recent note)
    @type count: int or NoneType
    @param count: number of recent notes to return (defaults to 10 notes)
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

  WHITESPACE_PATTERN = re.compile( "\s+" )
  NEWLINE_PATTERN = re.compile( "\r?\n" )

  @expose( view = Json )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    file_id = Valid_id(),
    content_column = Valid_int( min = 0 ),
    title_column = Valid_int( min = 0, none_okay = True ),
    plaintext = Valid_bool(),
    import_button = unicode,
    user_id = Valid_id( none_okay = True ),
  )
  def import_csv( self, file_id, content_column, title_column, plaintext, import_button, user_id = None ):
    """
    Import a previously uploaded CSV file of notes as a new notebook. Delete the file once the
    import is complete.

    Plaintext contents are left mostly untouched, just stripping HTML and converting newlines to
    <br> tags. HTML contents are cleaned of any disallowed/harmful HTML tags, and target="_new"
    attributes are added to all links without targets.

    @type file_id: unicode
    @param file_id: id of the previously uploaded CSV file to import
    @type content_column: int
    @param content_column: zero-based index of the column containing note contents
    @type title_column: int or NoneType
    @param title_column: zero-based index of the column containing note titles (None indicates
                         the lack of any such column, in which case titles are derived from the
                         first few words of each note's contents)
    @type plaintext: bool
    @param plaintext: True if the note contents are plaintext, or False if they're HTML
    @type import_button: unicode
    @param import_button: ignored
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: dict
    @return: { 'redirect': new_notebook_url }
    @raise Access_error: the current user doesn't have access to the given file
    @raise Files.Parse_error: there was an error in parsing the given file
    @raise Import_error: there was an error in importing the notes from the file
    """
    TRUNCATED_TITLE_CHAR_LENGTH = 80

    if user_id is None:
      raise Access_error()

    user = self.__database.load( User, user_id )
    if user is None:
      raise Access_error()

    db_file = self.__database.load( File, file_id )
    if db_file is None or not self.__users.check_access( user_id, db_file.notebook_id ):
      raise Access_error()

    parser = self.__files.parse_csv( file_id, skip_header = True )

    # create a new notebook for the imported notes
    notebook = self.__create_notebook( u"imported notebook", user, commit = False )

    # import the notes into the new notebook
    for row in parser:
      row_length = len( row )
      if content_column >= row_length:
        raise Import_error()
      if title_column is not None and title_column >= row_length:
        raise Import_error()

      # if there is a title column, use it. otherwise, use the first line of the content column as
      # the title
      if title_column and title_column != content_column and len( row[ title_column ].strip() ) > 0:
        title = Html_nuker( allow_refs = True ).nuke( Valid_string( escape_html = plaintext )( row[ title_column ].strip() ) )
      else:
        content_text = Html_nuker( allow_refs = True ).nuke( Valid_string( escape_html = plaintext )( row[ content_column ].strip() ) )
        content_lines = [ line for line in self.NEWLINE_PATTERN.split( content_text ) if line.strip() ]

        # skip notes with empty contents
        if len( content_lines ) == 0:
          continue

        title = content_lines[ 0 ]

        # truncate the makeshift title to a reasonable length, but truncate on a word boundary
        if len( title ) > TRUNCATED_TITLE_CHAR_LENGTH:
          title_words = self.WHITESPACE_PATTERN.split( title )

          for i in range( 1, len( title_words ) ):
            title_candidate = u" ".join( title_words[ : i ] )

            if len( title_candidate ) <= TRUNCATED_TITLE_CHAR_LENGTH:
              title = title_candidate
            else:
              break

      contents = u"<h3>%s</h3>%s" % (
        title,
        Valid_string( max = 25000, escape_html = plaintext, require_link_target = True )( row[ content_column ] ),
      )

      if plaintext:
        contents = contents.replace( u"\n", u"<br />" )

      note_id = self.__database.next_id( Note, commit = False )
      note = Note.create( note_id, contents, notebook_id = notebook.object_id, startup = False, rank = None, user_id = user_id )
      self.__database.save( note, commit = False )

    # delete the CSV file now that it's been imported
    self.__database.execute( db_file.sql_delete(), commit = False )
    self.__database.commit()
    Upload_file.delete_file( file_id )

    return dict(
      redirect = u"/notebooks/%s?rename=true" % notebook.object_id,
    )
