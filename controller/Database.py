import re
import os
import psycopg2 as psycopg
from psycopg2.pool import PersistentConnectionPool
import random


class Database( object ):
  ID_BITS = 128 # number of bits within an id
  ID_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"

  def __init__( self, connection = None ):
    """
    Create a new database and return it.

    @type connection: existing connection object with cursor()/close()/commit() methods, or NoneType
    @param connection: database connection to use (optional, defaults to making a connection pool)
    @rtype: Database
    @return: newly constructed Database
    """
    # This tells PostgreSQL to give us timestamps in UTC. I'd use "set timezone" instead, but that
    # makes SQLite angry.
    os.putenv( "PGTZ", "UTC" )

    if connection:
      self.__connection = connection
      self.__pool = None
    else:
      self.__connection = None
      self.__pool = PersistentConnectionPool(
        1,  # minimum connections
        50, # maximum connections
        "dbname=luminotes user=luminotes password=%s" % os.getenv( "PGPASSWORD", "dev" ),
      )

  def __get_connection( self ):
    if self.__connection:
      return self.__connection
    else:
      return self.__pool.getconn()

  def save( self, obj, commit = True ):
    """
    Save the given object to the database.

    @type obj: Persistent
    @param obj: object to save
    @type commit: bool
    @param commit: True to automatically commit after the save
    """
    connection = self.__get_connection()
    cursor = connection.cursor()

    cursor.execute( obj.sql_exists() )
    if cursor.fetchone():
      cursor.execute( obj.sql_update() )
    else:
      cursor.execute( obj.sql_create() )

    if commit:
      connection.commit()

  def commit( self ):
    self.__get_connection().commit()

  def load( self, Object_type, object_id, revision = None ):
    """
    Load the object corresponding to the given object id from the database and return it, or None if
    the object_id is unknown. If a revision is provided, a specific revision of the object will be
    loaded.

    @type Object_type: type
    @param Object_type: class of the object to load 
    @type object_id: unicode
    @param object_id: id of the object to load
    @type revision: int or NoneType
    @param revision: revision of the object to load (optional)
    @rtype: Object_type or NoneType
    @return: loaded object, or None if no match
    """
    return self.select_one( Object_type, Object_type.sql_load( object_id, revision ) )

  def select_one( self, Object_type, sql_command ):
    """
    Execute the given sql_command and return its results in the form of an object of Object_type,
    or None if there was no match.

    @type Object_type: type
    @param Object_type: class of the object to load 
    @type sql_command: unicode
    @param sql_command: SQL command to execute
    @rtype: Object_type or NoneType
    @return: loaded object, or None if no match
    """
    connection = self.__get_connection()
    cursor = connection.cursor()

    cursor.execute( sql_command )

    row = cursor.fetchone()
    if not row:
      return None

    if Object_type in ( tuple, list ):
      return Object_type( row )
    else:
      return Object_type( *row )

  def select_many( self, Object_type, sql_command ):
    """
    Execute the given sql_command and return its results in the form of a list of objects of
    Object_type.

    @type Object_type: type
    @param Object_type: class of the object to load 
    @type sql_command: unicode
    @param sql_command: SQL command to execute
    @rtype: list of Object_type
    @return: loaded objects
    """
    connection = self.__get_connection()
    cursor = connection.cursor()

    cursor.execute( sql_command )

    objects = []
    row = cursor.fetchone()

    while row:
      if Object_type in ( tuple, list ):
        obj = Object_type( row )
      else:
        obj = Object_type( *row )

      objects.append( obj )
      row = cursor.fetchone()

    return objects

  def execute( self, sql_command, commit = True ):
    """
    Execute the given sql_command.

    @type sql_command: unicode
    @param sql_command: SQL command to execute
    @type commit: bool
    @param commit: True to automatically commit after the command
    """
    connection = self.__get_connection()
    cursor = connection.cursor()

    cursor.execute( sql_command )

    if commit:
      connection.commit()

  @staticmethod
  def generate_id():
    int_id = random.getrandbits( Database.ID_BITS )

    base = len( Database.ID_DIGITS )
    digits = []

    while True:
      index = int_id % base
      digits.insert( 0, Database.ID_DIGITS[ index ] )
      int_id = int_id / base
      if int_id == 0:
        break

    return "".join( digits )

  def next_id( self, Object_type, commit = True ):
    """
    Generate the next available object id and return it.

    @type Object_type: type
    @param Object_type: class of the object that the id is for
    @type commit: bool
    @param commit: True to automatically commit after storing the next id
    """
    connection = self.__get_connection()
    cursor = connection.cursor()

    # generate a random id, but on the off-chance that it collides with something else already in
    # the database, try again
    next_id = Database.generate_id()
    cursor.execute( Object_type.sql_id_exists( next_id ) )

    while cursor.fetchone() is not None:
      next_id = Database.generate_id()
      cursor.execute( Object_type.sql_id_exists( next_id ) )

    # save a new object with the next_id to the database
    obj = Object_type( next_id )
    cursor.execute( obj.sql_create() )

    if commit:
      connection.commit()

    return next_id

  def close( self ):
    """
    Shutdown the database.
    """
    if self.__connection:
      self.__connection.close()

    if self.__pool:
      self.__pool.closeall()


class Valid_id( object ):
  """
  Validator for an object id.
  """
  ID_PATTERN = re.compile( "^[%s]+$" % Database.ID_DIGITS )

  def __init__( self, none_okay = False ):
    self.__none_okay = none_okay

  def __call__( self, value ):
    if self.__none_okay and value in ( None, "None", "" ): return None
    if self.ID_PATTERN.search( value ): return str( value )

    raise ValueError()


class Valid_revision( object ):
  """
  Validator for an object revision timestamp.
  """
  REVISION_PATTERN = re.compile( "^\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d\.\d+[+-]\d\d(:)?\d\d$" )

  def __init__( self, none_okay = False ):
    self.__none_okay = none_okay

  def __call__( self, value ):
    if self.__none_okay and value in ( None, "None", "" ): return None
    if self.REVISION_PATTERN.search( value ): return str( value )

    raise ValueError()
