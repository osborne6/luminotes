from copy import copy
from Entry import Entry
from Persistent import Persistent


class Notebook( Persistent ):
  """
  A collection of wiki entries.
  """

  class UnknownEntryError( ValueError ):
    """
    Indicates that an accessed entry is not in this notebook.
    """
    def __init__( self, entry_id ):
      ValueError.__init__( self, entry_id )

  def __init__( self, id, name ):
    """
    Create a new entry with the given id and name.

    @type id: unicode
    @param id: id of the notebook
    @type name: unicode
    @param name: name of this notebook
    @rtype: Notebook
    @return: newly constructed notebook
    """
    Persistent.__init__( self, id )
    self.__name = name
    self.__entries = {}         # map of entry id to entry
    self.__titles = {}          # map of entry title to entry
    self.__startup_entries = [] # list of entries shown on startup

  def add_entry( self, entry ):
    """
    Add an entry to this notebook.

    @type entry: Entry
    @param entry: entry to add
    """
    self.update_revision()
    self.__entries[ entry.object_id ] = entry
    self.__titles[ entry.title ] = entry

  def remove_entry( self, entry ):
    """
    Remove an entry from this notebook.

    @type entry: Entry
    @param entry: entry to remove
    @rtype: bool
    @return: True if the entry was removed, False if the entry wasn't in this notebook
    """
    if self.__entries.pop( entry.object_id, None ):
      self.update_revision()
      self.__titles.pop( entry.title, None )
      if entry in self.__startup_entries:
        self.__startup_entries.remove( entry )
      return True

    return False
      
  def lookup_entry( self, entry_id ):
    """
    Return the entry in this notebook with the given id.

    @type entry_id: unicode
    @param entry_id: id of the entry to return
    @rtype: Entry or NoneType
    @return: entry corresponding to the entry id or None
    """
    return self.__entries.get( entry_id )

  def lookup_entry_by_title( self, title ):
    """
    Return the entry in this notebook with the given title.

    @type title: unicode
    @param title: title of the entry to return
    @rtype: Entry or NoneType
    @return: entry corresponding to the title or None
    """
    return self.__titles.get( title )

  def update_entry( self, entry, contents ):
    """
    Update the given entry with new contents. Bail if the entry's contents are unchanged.

    @type entry: Entry
    @param entry: entry to update
    @type contents: unicode
    @param contents: new textual contents for the entry
    @raises UnknownEntryError: entry to update is not in this notebook
    """
    old_entry = self.__entries.get( entry.object_id )
    if old_entry is None:
      raise Notebook.UnknownEntryError( entry.object_id )

    if contents == old_entry.contents:
      return

    self.update_revision()
    self.__titles.pop( entry.title, None )

    entry.contents = contents

    self.__titles[ entry.title ] = entry

  def add_startup_entry( self, entry ):
    """
    Add the given entry to be shown on startup. It must already be an entry in this notebook.

    @type entry: unicode
    @param entry: entry to be added for startup
    @rtype: bool
    @return: True if the entry was added for startup
    @raises UnknownEntryError: given entry is not in this notebook
    """
    if self.__entries.get( entry.object_id ) is None:
      raise Notebook.UnknownEntryError( entry.object_id )
    
    if not entry in self.__startup_entries:
      self.update_revision()
      self.__startup_entries.append( entry )
      return True

    return False

  def remove_startup_entry( self, entry ):
    """
    Remove the given entry from being shown on startup.

    @type entry: unicode
    @param entry: entry to be removed from startup
    @rtype: bool
    @return: True if the entry was removed from startup
    """
    if entry in self.__startup_entries:
      self.update_revision()
      self.__startup_entries.remove( entry )
      return True

    return False

  def to_dict( self ):
    d = Persistent.to_dict( self )
    d.update( dict(
      name = self.__name,
      startup_entries = copy( self.startup_entries ),
      read_write = True,
    ) )

    return d

  def __set_name( self, name ):
    self.__name = name
    self.update_revision()

  name = property( lambda self: self.__name, __set_name )
  startup_entries = property( lambda self: copy( self.__startup_entries ) )
  entries = property( lambda self: self.__entries.values() )
