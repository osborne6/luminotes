import re
import os
import os.path
import sys
import sha
import cherrypy
import random
import threading
from model.Persistent import Persistent
from model.Notebook import Notebook


class Connection_wrapper( object ):
  def __init__( self, connection ):
    self.connection = connection
    self.pending_saves = []

  def __getattr__( self, name ):
    return getattr( self.connection, name )


def synchronized( method ):
  def lock( self, *args, **kwargs ):
    if self.lock:
      self.lock.acquire()

    try:
      return method( self, *args, **kwargs )
    finally:
      if self.lock:
        self.lock.release()

  return lock


class Database( object ):
  ID_BITS = 128 # number of bits within an id
  ID_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"

  # caching Notebooks causes problems because different users have different read_write/owner values
  CLASSES_NOT_TO_CACHE = ( Notebook, )

  def __init__( self, connection = None, cache = None, host = None, ssl_mode = None, data_dir = None ):
    """
    Create a new database and return it.

    @type connection: existing connection object with cursor()/close()/commit() methods, or NoneType
    @param connection: database connection to use (optional, defaults to making a connection pool)
    @type cache: cmemcache.Client or something with a similar API, or NoneType
    @param cache: existing memory cache to use (optional, defaults to making a cache)
    @type host: unicode or NoneType
    @param host: hostname of PostgreSQL database, or None to use a local SQLite database
    @type ssl_mode: unicode or NoneType
    @param ssl_mode: SSL mode for the database connection, one of "disallow", "allow", "prefer", or
                     "require". ignored if host is None
    @type data_dir: unicode or NoneType
    @param data_dir: directory in which to store data (defaults to a reasonable directory). ignored
                     if host is not None
    @rtype: Database
    @return: newly constructed Database
    """
    # This tells PostgreSQL to give us timestamps in UTC. I'd use "set timezone" instead, but that
    # makes SQLite angry.
    os.putenv( "PGTZ", "UTC" )

    if host is None:
      from pysqlite2 import dbapi2 as sqlite
      from datetime import datetime
      from pytz import utc

      TIMESTAMP_PATTERN = re.compile( "^(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d).(\d+)(?:\+\d\d:\d\d$)?" )

      def convert_timestamp( value ):
        ( year, month, day, hours, minutes, seconds, fractional_seconds ) = \
          TIMESTAMP_PATTERN.search( value ).groups( 0 )
        microseconds = int( float ( "0." + fractional_seconds ) * 1000000 )

        # ignore time zone in timestamp and assume UTC
        return datetime(
          int( year ), int( month ), int( day ),
          int( hours ), int( minutes ), int( seconds ), int( microseconds ),
          utc,
        )

      sqlite.register_converter( "boolean", lambda value: value in ( "t", "True", "true" ) and True or False )
      sqlite.register_converter( "timestamp", convert_timestamp )

      if connection:
        self.__connection = connection
      else:
        if data_dir is None:
          if sys.platform.startswith( "win" ):
            data_dir = os.path.join( os.environ.get( "APPDATA" ), "Luminotes" )
          else:
            data_dir = os.path.join( os.environ.get( "HOME", "" ), ".luminotes" )

        data_filename = os.path.join( data_dir, "luminotes.db" )

        # if the user doesn't yet have their own luminotes.db file, make them an initial copy
        if os.path.exists( "luminotes.db" ):
          if not os.path.exists( data_dir ):
            import stat
            os.makedirs( data_dir, stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR )

          if not os.path.exists( data_filename ):
            import shutil
            shutil.copyfile( "luminotes.db", data_filename )

        self.__connection = \
          Connection_wrapper( sqlite.connect( data_filename, detect_types = sqlite.PARSE_DECLTYPES, check_same_thread = False ) )
  
      self.__pool = None
      self.__backend = Persistent.SQLITE_BACKEND
      self.lock = threading.Lock() # multiple simultaneous client threads make SQLite angry
    else:
      import psycopg2 as psycopg
      from psycopg2.pool import PersistentConnectionPool

      # forcibly replace psycopg's connect() function with another function that returns the psycopg
      # connection wrapped in a class with a pending_saves member, used in save() and commit() below
      original_connect = psycopg.connect

      def connect( *args, **kwargs ):
        return Connection_wrapper( original_connect( *args, **kwargs ) )

      psycopg.connect = connect

      if connection:
        self.__connection = connection
        self.__pool = None
      else:
        self.__connection = None
        self.__pool = PersistentConnectionPool(
          1,  # minimum connections
          50, # maximum connections
          "host=%s sslmode=%s dbname=luminotes user=luminotes password=%s" % (
            host or "localhost",
            ssl_mode or "allow",
            os.getenv( "PGPASSWORD", "dev" )
          ),
        )

      self.__backend = Persistent.POSTGRESQL_BACKEND
      self.lock = None # PostgreSQL does its own synchronization

    self.__cache = cache

    try:
      if self.__cache is None:
        import cmemcache
        print "using memcached"
    except ImportError:
      return None

  def __get_connection( self ):
    if self.__connection:
      return self.__connection
    else:
      return self.__pool.getconn()

  def __get_cache_connection( self ):
    if self.__cache is not None:
      return self.__cache

    try:
      import cmemcache
      return cmemcache.Client( [ "127.0.0.1:11211" ], debug = 0 )
    except ImportError:
      return None

  @synchronized
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

    if isinstance( obj, self.CLASSES_NOT_TO_CACHE ):
      cache = None
    else:
      cache = self.__get_cache_connection()

    if commit:
      connection.commit()
      if cache:
        cache.set( obj.cache_key, obj )
    elif cache:
      # no commit yet, so don't touch the cache
      connection.pending_saves.append( obj )

  @synchronized
  def commit( self ):
    connection = self.__get_connection()
    connection.commit()

    # save any pending saves to the cache
    cache = self.__get_cache_connection()

    if cache:
      for obj in connection.pending_saves:
        cache.set( obj.cache_key, obj )

      connection.pending_saves = []

  @synchronized
  def rollback( self ):
    connection = self.__get_connection()
    connection.rollback()

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
    if revision or Object_type in self.CLASSES_NOT_TO_CACHE:
      cache = None
    else:
      cache = self.__get_cache_connection()

    if cache: # don't bother caching old revisions
      obj = cache.get( Persistent.make_cache_key( Object_type, object_id ) )
      if obj:
        return obj

    obj = self.select_one( Object_type, Object_type.sql_load( object_id, revision ) )
    if obj and cache:
      cache.set( obj.cache_key, obj )

    return obj

  @synchronized
  def select_one( self, Object_type, sql_command, use_cache = False ):
    """
    Execute the given sql_command and return its results in the form of an object of Object_type,
    or None if there was no match.

    @type Object_type: type
    @param Object_type: class of the object to load 
    @type sql_command: unicode
    @param sql_command: SQL command to execute
    @type use_cache: bool
    @param use_cache: whether to look for and store objects in the cache
    @rtype: Object_type or NoneType
    @return: loaded object, or None if no match
    """
    if not use_cache or Object_type in self.CLASSES_NOT_TO_CACHE:
      cache = None
    else:
      cache = self.__get_cache_connection()

    if cache:
      cache_key = sha.new( sql_command ).hexdigest()
      obj = cache.get( cache_key )
      if obj:
        return obj

    connection = self.__get_connection()
    cursor = connection.cursor()

    cursor.execute( sql_command )

    row = self.__row_to_unicode( cursor.fetchone() )
    if not row:
      return None

    if Object_type in ( tuple, list ):
      obj = Object_type( row )
    else:
      obj = Object_type( *row )

    if obj and cache:
      cache.set( cache_key, obj )

    return obj

  @synchronized
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
    row = self.__row_to_unicode( cursor.fetchone() )

    while row:
      if Object_type in ( tuple, list ):
        obj = Object_type( row )
      else:
        obj = Object_type( *row )

      objects.append( obj )
      row = self.__row_to_unicode( cursor.fetchone() )

    return objects

  def __row_to_unicode( self, row ):
    if row is None:
      return None

    return [ isinstance( item, str ) and unicode( item, encoding = "utf8" ) or item for item in row ]

  @synchronized
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

  @synchronized
  def execute_script( self, sql_commands, commit = True ):
    """
    Execute the given sql_commands.

    @type sql_command: unicode
    @param sql_command: multiple SQL commands to execute
    @type commit: bool
    @param commit: True to automatically commit after the command
    """
    connection = self.__get_connection()
    cursor = connection.cursor()

    if self.__backend == Persistent.SQLITE_BACKEND:
      cursor.executescript( sql_commands )
    else:
      cursor.execute( sql_commands )

    if commit:
      connection.commit()

  def uncache_command( self, sql_command ):
    cache = self.__get_cache_connection()
    if not cache: return

    cache_key = sha.new( sql_command ).hexdigest()
    cache.delete( cache_key )

  def uncache( self, obj ):
    cache = self.__get_cache_connection()
    if not cache: return

    cache.delete( obj.cache_key )

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

  @synchronized
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

  @synchronized
  def close( self ):
    """
    Shutdown the database.
    """
    if self.__connection:
      self.__connection.close()

    if self.__pool:
      self.__pool.closeall()

  backend = property( lambda self: self.__backend )


def end_transaction( function ):
  """
  Decorator that prevents transaction leaks by rolling back any transactions left open when the
  wrapped function returns or raises.
  """
  def rollback( *args, **kwargs ):
    try:
      return function( *args, **kwargs )
    finally:
      cherrypy.root.database.rollback()

  return rollback


class Valid_id( object ):
  """
  Validator for an object id.
  """
  ID_PATTERN = re.compile( "^[%s]+$" % Database.ID_DIGITS )

  def __init__( self, none_okay = False ):
    self.__none_okay = none_okay

  def __call__( self, value ):
    if value in ( None, "None", "" ):
      if self.__none_okay:
        return None
      else:
        raise ValueError()

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
