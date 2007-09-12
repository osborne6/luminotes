import re
import bsddb
import random
import cPickle
from cStringIO import StringIO
from copy import copy
from model.Persistent import Persistent
from Async import async


class Database( object ):
  ID_BITS = 128 # number of bits within an id
  ID_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"

  def __init__( self, scheduler, database_path = None ):
    """
    Create a new database and return it.

    @type scheduler: Scheduler
    @param scheduler: scheduler to use
    @type database_path: unicode
    @param database_path: path to the database file
    @rtype: Database
    @return: database at the given path
    """
    self.__scheduler = scheduler
    self.__env = bsddb.db.DBEnv()
    self.__env.open( None, bsddb.db.DB_CREATE | bsddb.db.DB_PRIVATE | bsddb.db.DB_INIT_MPOOL )
    self.__db = bsddb.db.DB( self.__env )
    self.__db.open( database_path, "database", bsddb.db.DB_HASH, bsddb.db.DB_CREATE )
    self.__cache = {}

  def __persistent_id( self, obj, skip = None ):
    # save the object and return its persistent id
    if obj != skip and isinstance( obj, Persistent ):
      self.__save( obj )
      return obj.object_id

    # returning None indicates that the object should be pickled normally without using a persistent id
    return None

  @async
  def save( self, obj, callback = None ):
    """
    Save the given object to the database, including any objects that it references.

    @type obj: Persistent
    @param obj: object to save
    @type callback: generator or NoneType
    @param callback: generator to wakeup when the save is complete (optional)
    """
    self.__save( obj )
    yield callback

  def __save( self, obj ):
    # if this object's current revision is already saved, bail
    revision_id = obj.revision_id()
    if revision_id in self.__cache:
      return

    object_id = unicode( obj.object_id ).encode( "utf8" )
    revision_id = unicode( obj.revision_id() ).encode( "utf8" )
    secondary_id = obj.secondary_id and unicode( obj.full_secondary_id() ).encode( "utf8" ) or None

    # update the cache with this saved object
    self.__cache[ object_id ] = obj
    self.__cache[ revision_id ] = copy( obj )
    if secondary_id:
      self.__cache[ secondary_id ] = obj

    # set the pickler up to save persistent ids for every object except for the obj passed in, which
    # will be pickled normally
    buffer = StringIO()
    pickler = cPickle.Pickler( buffer, protocol = -1 )
    pickler.persistent_id = lambda o: self.__persistent_id( o, skip = obj )

    # pickle the object and write it to the database under both its id key and its revision id key
    pickler.dump( obj )
    pickled = buffer.getvalue()
    self.__db.put( object_id, pickled )
    self.__db.put( revision_id, pickled )

    # write the pickled object id (only) to the database under its secondary id
    if secondary_id:
      buffer = StringIO()
      pickler = cPickle.Pickler( buffer, protocol = -1 )
      pickler.persistent_id = lambda o: self.__persistent_id( o )
      pickler.dump( obj )
      self.__db.put( secondary_id, buffer.getvalue() )

    self.__db.sync()

  @async
  def load( self, object_id, callback, revision = None ):
    """
    Load the object corresponding to the given object id from the database, and yield the provided
    callback generator with the loaded object as its argument, or None if the object_id is unknown.
    If a revision is provided, a specific revision of the object will be loaded.

    @type object_id: unicode
    @param object_id: id of the object to load
    @type callback: generator
    @param callback: generator to send the loaded object to
    @type revision: int or NoneType
    @param revision: revision of the object to load (optional)
    """
    obj = self.__load( object_id, revision )
    yield callback, obj

  def __load( self, object_id, revision = None ):
    if revision is not None:
      object_id = Persistent.make_revision_id( object_id, revision )

    object_id = unicode( object_id ).encode( "utf8" )

    # if the object corresponding to the given id has already been loaded, simply return it without
    # loading it again
    obj = self.__cache.get( object_id )
    if obj is not None:
      return obj

    # grab the object for the given id from the database
    buffer = StringIO()
    unpickler = cPickle.Unpickler( buffer )
    unpickler.persistent_load = self.__load

    pickled = self.__db.get( object_id )
    if pickled is None or pickled == "":
      return None

    buffer.write( pickled )
    buffer.flush()
    buffer.seek( 0 )

    # unpickle the object and update the cache with this saved object
    obj = unpickler.load()
    if obj is None:
      print "error unpickling %s: %s" % ( object_id, pickled )
      return None
    self.__cache[ unicode( obj.object_id ).encode( "utf8" ) ] = obj
    self.__cache[ unicode( obj.revision_id() ).encode( "utf8" ) ] = copy( obj )

    return obj

  @async
  def reload( self, object_id, callback = None ):
    """
    Load and immediately save the object corresponding to the given object id or database key. This
    is useful when the object has a __setstate__() method that performs some sort of schema
    evolution operation.

    @type object_id: unicode
    @param object_id: id or key of the object to reload
    @type callback: generator or NoneType
    @param callback: generator to wakeup when the save is complete (optional)
    """
    self.__reload( object_id )
    yield callback

  def __reload( self, object_id, revision = None ):
    object_id = unicode( object_id ).encode( "utf8" )

    # grab the object for the given id from the database
    buffer = StringIO()
    unpickler = cPickle.Unpickler( buffer )
    unpickler.persistent_load = self.__load

    pickled = self.__db.get( object_id )
    if pickled is None or pickled == "":
      return

    buffer.write( pickled )
    buffer.flush()
    buffer.seek( 0 )

    # unpickle the object. this should trigger __setstate__() if the object has such a method
    obj = unpickler.load()
    if obj is None:
      print "error unpickling %s: %s" % ( object_id, pickled )
      return
    self.__cache[ object_id ] = obj

    # set the pickler up to save persistent ids for every object except for the obj passed in, which
    # will be pickled normally
    buffer = StringIO()
    pickler = cPickle.Pickler( buffer, protocol = -1 )
    pickler.persistent_id = lambda o: self.__persistent_id( o, skip = obj )

    # pickle the object and write it to the database under its id key
    pickler.dump( obj )
    pickled = buffer.getvalue()
    self.__db.put( object_id, pickled )

    self.__db.sync()

  def size( self, object_id, revision = None ):
    """
    Load the object corresponding to the given object id from the database, and return the size of
    its pickled data in bytes. If a revision is provided, a specific revision of the object will be
    loaded.

    @type object_id: unicode
    @param object_id: id of the object whose size should be returned
    @type revision: int or NoneType
    @param revision: revision of the object to load (optional)
    """
    if revision is not None:
      object_id = Persistent.make_revision_id( object_id, revision )

    object_id = unicode( object_id ).encode( "utf8" )

    pickled = self.__db.get( object_id )
    if pickled is None or pickled == "":
      return None

    return len( pickled )

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

  @async
  def next_id( self, callback ):
    """
    Generate the next available object id, and yield the provided callback generator with the
    object id as its argument.

    @type callback: generator
    @param callback: generator to send the next available object id to
    """
    # generate a random id, but on the off-chance that it collides with something else already in
    # the database, try again
    next_id = Database.generate_id()
    while self.__db.get( next_id, default = None ) is not None:
      next_id = Database.generate_id()

    # save the next_id as a key in the database so that it's not handed out again to another client
    self.__db[ next_id ] = ""

    yield callback, next_id

  @async
  def close( self ):
    """
    Shutdown the database.
    """
    self.__db.close()
    self.__env.close()
    yield None

  @async
  def clear_cache( self ):
    """
    Clear the memory object cache.
    """
    self.__cache.clear()
    yield None

  scheduler = property( lambda self: self.__scheduler )


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
  Validator for an object id.
  """
  REVISION_PATTERN = re.compile( "^\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d\.\d+$" )

  def __init__( self, none_okay = False ):
    self.__none_okay = none_okay

  def __call__( self, value ):
    if self.__none_okay and value in ( None, "None", "" ): return None
    if self.REVISION_PATTERN.search( value ): return str( value )

    raise ValueError()
