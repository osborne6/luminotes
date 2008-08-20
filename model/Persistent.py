from datetime import datetime
from pytz import utc


class Persistent( object ):
  POSTGRESQL_BACKEND = 0
  SQLITE_BACKEND = 1

  """
  A persistent database object with a unique id.
  """
  def __init__( self, object_id, revision = None ):
    self.__object_id = object_id
    self.__revision = revision

    if not revision:
      self.update_revision()

  @staticmethod
  def sql_load( object_id, revision = None ):
    """
    Return a SQL string to load an object with the given information from the database. If a
    revision is not provided, then the most current version of the given object will be loaded.

    @type object_id: unicode
    @param object_id: id of object to load
    @type revision: unicode or NoneType
    @param revision: revision of the object to load (optional)
    """
    raise NotImplementedError()

  @staticmethod
  def sql_id_exists( object_id, revision = None ):
    """
    Return a SQL string to determine whether the given object is present in the database. If a
    revision is not provided, then the most current version of the given object will be used.

    @type object_id: unicode
    @param object_id: id of object to check for existence
    @type revision: unicode or NoneType
    @param revision: revision of the object to check (optional)
    """
    raise NotImplementedError()

  def sql_exists( self ):
    """
    Return a SQL string to determine whether the current revision of this object is present in the
    database.
    """
    raise NotImplementedError()

  def sql_create( self ):
    """
    Return a SQL string to save this object to the database for the first time. This should be in
    the form of a SQL insert.
    """
    raise NotImplementedError()

  def sql_update( self ):
    """
    Return a SQL string to save an updated revision of this object to the database. Note that,
    because of the retention of old row revisions in the database, this SQL string will usually
    be in the form of an insert rather than an update to an existing row.
    """
    raise NotImplementedError()

  def to_dict( self ):
    return dict(
      object_id = self.__object_id,
      revision = self.__revision,
    )

  def update_revision( self ):
    self.__revision = datetime.now( tz = utc )

  @staticmethod
  def make_cache_key( Object_type, object_id ):
    return "%s_%s" % ( object_id, Object_type.__name__ )

  object_id = property( lambda self: self.__object_id )
  revision = property( lambda self: self.__revision )
  cache_key = property( lambda self: Persistent.make_cache_key( type( self ), self.object_id ) )


def quote( value ):
  if value is None:
    return "null"

  if isinstance( value, bool ):
    value = value and "t" or "f"
  else:
    value = unicode( value )

  return "'%s'" % value.replace( "'", "''" ).replace( "\\", "\\\\" )


def quote_fuzzy( value ):
  if value is None:
    return "null"

  value = unicode( value )

  value = value.replace( "'", "''" ).replace( "\\", "\\\\" )
  return "'%" + value + "%'"
