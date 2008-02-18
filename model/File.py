from Persistent import Persistent, quote
from psycopg2 import Binary
from StringIO import StringIO


class File( Persistent ):
  """
  Metadata about an uploaded file. The actual file data is stored on the filesystem instead of in
  the database. (Binary conversion to/from PostgreSQL's bytea is too slow, and the version of
  psycopg2 I'm using doesn't have large object support.)
  """
  def __init__( self, object_id, revision = None, notebook_id = None, note_id = None,
                filename = None, size_bytes = None ):
    """
    Create a File with the given id.

    @type object_id: unicode
    @param object_id: id of the File
    @type revision: datetime or NoneType
    @param revision: revision timestamp of the object (optional, defaults to now)
    @type notebook_id: unicode or NoneType
    @param notebook_id: id of the notebook containing the file
    @type note_id: unicode or NoneType
    @param note_id: id of the note linking to the file
    @type filename: unicode
    @param filename: name of the file on the client
    @type size_bytes: int
    @param size_bytes: length of the file data in bytes
    @rtype: File
    @return: newly constructed File
    """
    Persistent.__init__( self, object_id, revision )
    self.__notebook_id = notebook_id
    self.__note_id = note_id
    self.__filename = filename
    self.__size_bytes = size_bytes

  @staticmethod
  def create( object_id, notebook_id = None, note_id = None, filename = None, size_bytes = None ):
    """
    Convenience constructor for creating a new File.

    @type object_id: unicode
    @param object_id: id of the File
    @type notebook_id: unicode or NoneType
    @param notebook_id: id of the notebook containing the file
    @type note_id: unicode or NoneType
    @param note_id: id of the note linking to the file
    @type filename: unicode
    @param filename: name of the file on the client
    @type size_bytes: int
    @param size_bytes: length of the file data in bytes
    @rtype: File
    @return: newly constructed File
    """
    return File( object_id, notebook_id = notebook_id, note_id = note_id, filename = filename,
                 size_bytes = size_bytes )

  @staticmethod
  def sql_load( object_id, revision = None ):
    # Files don't store old revisions
    if revision:
      raise NotImplementedError()

    return \
      """
      select
        file.id, file.revision, file.notebook_id, file.note_id, file.filename, size_bytes
      from
        file
      where
        file.id = %s;
      """ % quote( object_id )

  @staticmethod
  def sql_id_exists( object_id, revision = None ):
    if revision:
      raise NotImplementedError()

    return "select id from file where id = %s;" % quote( object_id )

  def sql_exists( self ):
    return File.sql_id_exists( self.object_id )

  def sql_create( self ):
    return "insert into file ( id, revision, notebook_id, note_id, filename, size_bytes ) values ( %s, %s, %s, %s, %s, %s );" % \
    ( quote( self.object_id ), quote( self.revision ), quote( self.__notebook_id ), quote( self.__note_id ),
      quote( self.__filename ), self.__size_bytes or 'null' )

  def sql_update( self ):
    return "update file set revision = %s, notebook_id = %s, note_id = %s, filename = %s, size_bytes = %s where id = %s;" % \
    ( quote( self.revision ), quote( self.__notebook_id ), quote( self.__note_id ), quote( self.__filename ),
      self.__size_bytes or 'null', quote( self.object_id ) )

  def to_dict( self ):
    d = Persistent.to_dict( self )
    d.update( dict(
      notebook_id = self.__notebook_id,
      note_id = self.__note_id,
      filename = self.__filename,
      size_bytes = self.__size_bytes,
    ) )

    return d

  notebook_id = property( lambda self: self.__notebook_id )
  note_id = property( lambda self: self.__note_id )
  filename = property( lambda self: self.__filename )
  size_bytes = property( lambda self: self.__size_bytes )
