from copy import copy
from Note import Note
from Persistent import Persistent, quote


class Notebook( Persistent ):
  """
  A collection of wiki notes.
  """
  def __init__( self, object_id, revision = None, name = None, trash_id = None, read_write = True ):
    """
    Create a new notebook with the given id and name.

    @type object_id: unicode
    @param object_id: id of the notebook
    @type revision: datetime or NoneType
    @param revision: revision timestamp of the object (optional, defaults to now)
    @type name: unicode or NoneType
    @param name: name of this notebook (optional)
    @type trash_id: Notebook or NoneType
    @param trash_id: id of the notebook where deleted notes from this notebook go to die (optional)
    @type read_write: bool or NoneType
    @param read_write: whether this view of the notebook is currently read-write (optional, defaults to True)
    @rtype: Notebook
    @return: newly constructed notebook
    """
    Persistent.__init__( self, object_id, revision )
    self.__name = name
    self.__trash_id = trash_id
    self.__read_write = read_write

  @staticmethod
  def create( object_id, name = None, trash_id = None, read_write = True ):
    """
    Convenience constructor for creating a new notebook.

    @type object_id: unicode
    @param object_id: id of the notebook
    @type name: unicode or NoneType
    @param name: name of this notebook (optional)
    @type trash_id: Notebook or NoneType
    @param trash_id: id of the notebook where deleted notes from this notebook go to die (optional)
    @type read_write: bool or NoneType
    @param read_write: whether this view of the notebook is currently read-write (optional, defaults to True)
    @rtype: Notebook
    @return: newly constructed notebook
    """
    return Notebook( object_id, name = name, trash_id = trash_id, read_write = read_write )

  @staticmethod
  def sql_load( object_id, revision = None ):
    if revision:
      return "select * from notebook where id = %s and revision = %s;" % ( quote( object_id ), quote( revision ) )

    return "select * from notebook_current where id = %s;" % quote( object_id )

  @staticmethod
  def sql_id_exists( object_id, revision = None ):
    if revision:
      return "select id from notebook where id = %s and revision = %s;" % ( quote( object_id ), quote( revision ) )

    return "select id from notebook_current where id = %s;" % quote( object_id )

  def sql_exists( self ):
    return Notebook.sql_id_exists( self.object_id, self.revision )

  def sql_create( self ):
    return \
      "insert into notebook ( id, revision, name, trash_id ) " + \
      "values ( %s, %s, %s, %s );" % \
      ( quote( self.object_id ), quote( self.revision ), quote( self.__name ),
        quote( self.__trash_id ) )

  def sql_update( self ):
    return self.sql_create()

  def sql_load_notes( self ):
    """
    Return a SQL string to load a list of all the notes within this notebook.
    """
    return "select * from note_current where notebook_id = %s order by revision desc;" % quote( self.object_id )

  def sql_load_non_startup_notes( self ):
    """
    Return a SQL string to load a list of the non-startup notes within this notebook.
    """
    return "select * from note_current where notebook_id = %s and startup = 'f' order by revision desc;" % quote( self.object_id )

  def sql_load_startup_notes( self ):
    """
    Return a SQL string to load a list of the startup notes within this notebook.
    """
    return "select * from note_current where notebook_id = %s and startup = 't' order by rank;" % quote( self.object_id )

  def sql_load_note_by_id( self, note_id ):
    """
    Return a SQL string to load a particular note within this notebook by the note's id.

    @type note_id: unicode
    @param note_id: id of note to load
    """
    return "select * from note_current where notebook_id = %s and id = %s;" % ( quote( self.object_id ), quote( note_id ) )

  def sql_load_note_by_title( self, title ):
    """
    Return a SQL string to load a particular note within this notebook by the note's title.

    @type note_id: unicode
    @param note_id: title of note to load
    """
    return "select * from note_current where notebook_id = %s and title = %s;" % ( quote( self.object_id ), quote( title ) )

  def sql_search_notes( self, search_text ):
    """
    Return a SQL string to search for notes whose contents contain the given search_text. This
    is a case-insensitive search.

    @type search_text: unicode
    @param search_text: text to search for within the notes
    """
    return \
      "select * from note_current where notebook_id = %s and contents ilike %s;" % \
      ( quote( self.object_id ), quote( "%" + search_text + "%" ) )

  def sql_highest_rank( self ):
    return "select coalesce( max( rank ), -1 ) from note_current where notebook_id = %s;" % quote( self.object_id )

  def to_dict( self ):
    d = Persistent.to_dict( self )

    d.update( dict(
      name = self.__name,
      trash_id = self.__trash_id,
      read_write = self.__read_write,
    ) )

    return d

  def __set_name( self, name ):
    self.__name = name
    self.update_revision()

  def __set_read_write( self, read_write ):
    self.__read_write = read_write

  name = property( lambda self: self.__name, __set_name )
  trash_id = property( lambda self: self.__trash_id )
  read_write = property( lambda self: self.__read_write, __set_read_write )