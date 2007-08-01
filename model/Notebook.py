from copy import copy
from Note import Note
from Persistent import Persistent


class Notebook( Persistent ):
  """
  A collection of wiki notes.
  """

  class UnknownNoteError( ValueError ):
    """
    Indicates that an accessed note is not in this notebook.
    """
    def __init__( self, note_id ):
      ValueError.__init__( self, note_id )

  def __init__( self, id, name ):
    """
    Create a new note with the given id and name.

    @type id: unicode
    @param id: id of the notebook
    @type name: unicode
    @param name: name of this notebook
    @rtype: Notebook
    @return: newly constructed notebook
    """
    Persistent.__init__( self, id )
    self.__name = name
    self.__notes = {}         # map of note id to note
    self.__titles = {}        # map of note title to note
    self.__startup_notes = [] # list of notes shown on startup

  def add_note( self, note ):
    """
    Add a note to this notebook.

    @type note: Note
    @param note: note to add
    """
    self.update_revision()
    self.__notes[ note.object_id ] = note
    self.__titles[ note.title ] = note

  def remove_note( self, note ):
    """
    Remove a note from this notebook.

    @type note: Note
    @param note: note to remove
    @rtype: bool
    @return: True if the note was removed, False if the note wasn't in this notebook
    """
    if self.__notes.pop( note.object_id, None ):
      self.update_revision()
      self.__titles.pop( note.title, None )
      if self.is_startup_note( note ):
        self.__startup_notes.remove( note )
      return True

    return False
      
  def lookup_note( self, note_id ):
    """
    Return the note in this notebook with the given id.

    @type note_id: unicode
    @param note_id: id of the note to return
    @rtype: Note or NoneType
    @return: note corresponding to the note id or None
    """
    return self.__notes.get( note_id )

  def lookup_note_by_title( self, title ):
    """
    Return the note in this notebook with the given title.

    @type title: unicode
    @param title: title of the note to return
    @rtype: Note or NoneType
    @return: note corresponding to the title or None
    """
    return self.__titles.get( title )

  def update_note( self, note, contents ):
    """
    Update the given note with new contents. Bail if the note's contents are unchanged.

    @type note: Note
    @param note: note to update
    @type contents: unicode
    @param contents: new textual contents for the note
    @raises UnknownNoteError: note to update is not in this notebook
    """
    old_note = self.__notes.get( note.object_id )
    if old_note is None:
      raise Notebook.UnknownNoteError( note.object_id )

    if contents == old_note.contents:
      return

    self.update_revision()
    self.__titles.pop( note.title, None )

    note.contents = contents

    self.__titles[ note.title ] = note

  def add_startup_note( self, note ):
    """
    Add the given note to be shown on startup. It must already be a note in this notebook.

    @type note: Note
    @param note: note to be added for startup
    @rtype: bool
    @return: True if the note was added for startup
    @raises UnknownNoteError: given note is not in this notebook
    """
    if self.__notes.get( note.object_id ) is None:
      raise Notebook.UnknownNoteError( note.object_id )

    if not self.is_startup_note( note ):
      self.update_revision()
      self.__startup_notes.append( note )
      return True

    return False

  def remove_startup_note( self, note ):
    """
    Remove the given note from being shown on startup.

    @type note: Note
    @param note: note to be removed from startup
    @rtype: bool
    @return: True if the note was removed from startup
    """
    if self.is_startup_note( note ):
      self.update_revision()
      self.__startup_notes.remove( note )
      return True

    return False

  def is_startup_note( self, note ):
    """
    Return whether the given note is a startup note.

    @type note: Note
    @param note: note to test for startup status
    @rtype bool
    @return: True if the note is a startup note
    """
    return note.object_id in [ n.object_id for n in self.__startup_notes if n ]

  def to_dict( self ):
    d = Persistent.to_dict( self )
    d.update( dict(
      name = self.__name,
      startup_notes = copy( self.startup_notes ),
      read_write = True,
    ) )

    return d

  def __set_name( self, name ):
    self.__name = name
    self.update_revision()

  name = property( lambda self: self.__name, __set_name )
  startup_notes = property( lambda self: copy( self.__startup_notes ) )
  notes = property( lambda self: self.__notes.values() )
