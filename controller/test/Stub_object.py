from datetime import datetime
from new_model.Persistent import Persistent, quote


def notz_quote( value ):
  """
  Apparently, pysqlite2 chokes on timestamps that have a timezone when reading them out of the
  database, so for purposes of the unit tests, strip off the timezone on all datetime objects.
  """
  if isinstance( value, datetime ):
    value = value.replace( tzinfo = None )

  return quote( value )


class Stub_object( Persistent ):
  def __init__( self, object_id, revision = None, value = None, value2 = None ):
    Persistent.__init__( self, object_id, revision )
    self.__value = value
    self.__value2 = value2

  @staticmethod
  def sql_load( object_id, revision = None ):
    if revision:
      return "select * from stub_object where id = %s and revision = %s;" % ( quote( object_id ), notz_quote( revision ) )

    return "select * from stub_object where id = %s order by revision desc limit 1;" % quote( object_id )

  @staticmethod
  def sql_id_exists( object_id, revision = None ):
    if revision:
      return "select id from stub_object where id = %s and revision = %s;" % ( quote( object_id ), notz_quote( revision ) )

    return "select id from stub_object where id = %s order by revision desc limit 1;" % quote( object_id )

  def sql_exists( self ):
    return Stub_object.sql_id_exists( self.object_id, self.revision )

  def sql_create( self ):
    return \
      "insert into stub_object ( id, revision, value, value2 ) " + \
      "values ( %s, %s, %s, %s );" % \
      ( quote( self.object_id ), notz_quote( self.revision ), quote( self.__value ),
        quote( self.__value2 ) )

  def sql_update( self ):
    return self.sql_create()

  @staticmethod
  def sql_load_em_all():
    return "select * from stub_object;"

  @staticmethod
  def sql_create_table():
    return \
      """
      create table stub_object (
        id text not null,
        revision timestamp with time zone not null,
        value integer,
        value2 integer
      );
      """

  @staticmethod
  def sql_tuple():
    return "select 1, 2;"

  def __set_value( self, value ):
    self.update_revision()
    self.__value = value

  def __set_value2( self, value2 ):
    self.update_revision()
    self.__value2 = value2

  value = property( lambda self: self.__value, __set_value )
  value2 = property( lambda self: self.__value2, __set_value2 )

