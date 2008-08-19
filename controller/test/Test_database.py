from pytz import utc
from pysqlite2 import dbapi2 as sqlite
from datetime import datetime
from Stub_object import Stub_object
from Stub_cache import Stub_cache
from controller.Database import Database, Connection_wrapper


class Test_database( object ):
  def setUp( self ):
    # make an in-memory sqlite database to use in place of PostgreSQL during testing
    self.connection = Connection_wrapper( sqlite.connect( ":memory:", detect_types = sqlite.PARSE_DECLTYPES ) )
    self.cache = Stub_cache()
    cursor = self.connection.cursor()
    cursor.execute( Stub_object.sql_create_table() )

    self.database = Database( self.connection, self.cache )

  def tearDown( self ):
    self.database.close()

  def test_save_and_load( self ):
    basic_obj = Stub_object( object_id = "5", value = 1 )
    original_revision = basic_obj.revision

    self.database.save( basic_obj )
    obj = self.database.load( Stub_object, basic_obj.object_id )

    assert obj.object_id == basic_obj.object_id
    assert obj.revision.replace( tzinfo = utc ) == original_revision
    assert obj.value == basic_obj.value

  def test_save_and_load_without_commit( self ):
    basic_obj = Stub_object( object_id = "5", value = 1 )
    original_revision = basic_obj.revision

    self.database.save( basic_obj, commit = False )
    self.connection.rollback() # if commit wasn't called, this should back out the save
    obj = self.database.load( Stub_object, basic_obj.object_id )

    assert obj == None

  def test_save_and_load_with_explicit_commit( self ):
    basic_obj = Stub_object( object_id = "5", value = 1 )
    original_revision = basic_obj.revision

    self.database.save( basic_obj, commit = False )
    self.database.commit()
    self.connection.rollback() # should have no effect because of the call to commit
    obj = self.database.load( Stub_object, basic_obj.object_id )

    assert obj.object_id == basic_obj.object_id
    assert obj.revision.replace( tzinfo = utc ) == original_revision
    assert obj.value == basic_obj.value

  def test_select_one( self ):
    basic_obj = Stub_object( object_id = "5", value = 1 )
    original_revision = basic_obj.revision

    self.database.save( basic_obj )
    obj = self.database.select_one( Stub_object, Stub_object.sql_load( basic_obj.object_id ) )

    assert obj.object_id == basic_obj.object_id
    assert obj.revision.replace( tzinfo = utc ) == original_revision
    assert obj.value == basic_obj.value

  def test_select_one_tuple( self ):
    obj = self.database.select_one( tuple, Stub_object.sql_tuple() )

    assert len( obj ) == 2
    assert obj[ 0 ] == 1
    assert obj[ 1 ] == 2

  def test_select_many( self ):
    basic_obj = Stub_object( object_id = "5", value = 1 )
    original_revision = basic_obj.revision
    basic_obj2 = Stub_object( object_id = "6", value = 2 )
    original_revision2 = basic_obj2.revision

    self.database.save( basic_obj )
    self.database.save( basic_obj2 )
    objs = self.database.select_many( Stub_object, Stub_object.sql_load_em_all() )

    assert len( objs ) == 2
    assert objs[ 0 ].object_id == basic_obj.object_id
    assert objs[ 0 ].revision.replace( tzinfo = utc ) == original_revision
    assert objs[ 0 ].value == basic_obj.value
    assert objs[ 1 ].object_id == basic_obj2.object_id
    assert objs[ 1 ].revision.replace( tzinfo = utc ) == original_revision2
    assert objs[ 1 ].value == basic_obj2.value

  def test_select_many_tuples( self ):
    objs = self.database.select_many( tuple, Stub_object.sql_tuple() )

    assert len( objs ) == 1
    assert len( objs[ 0 ] ) == 2
    assert objs[ 0 ][ 0 ] == 1
    assert objs[ 0 ][ 1 ] == 2

  def test_select_many_with_no_matches( self ):
    objs = self.database.select_many( Stub_object, Stub_object.sql_load_em_all() )

    assert len( objs ) == 0

  def test_save_and_load_revision( self ):
    basic_obj = Stub_object( object_id = "5", value = 1 )
    original_revision = basic_obj.revision

    self.database.save( basic_obj )
    basic_obj.value = 2

    self.database.save( basic_obj )
    obj = self.database.load( Stub_object, basic_obj.object_id )

    assert obj.object_id == basic_obj.object_id
    assert obj.revision.replace( tzinfo = utc ) == basic_obj.revision
    assert obj.value == basic_obj.value

    revised = self.database.load( Stub_object, basic_obj.object_id, revision = original_revision )

    assert revised.object_id == basic_obj.object_id
    assert revised.value == 1
    assert revised.revision.replace( tzinfo = utc ) == original_revision

  def test_execute( self ):
    basic_obj = Stub_object( object_id = "5", value = 1 )
    original_revision = basic_obj.revision

    self.database.execute( basic_obj.sql_create() )
    obj = self.database.load( Stub_object, basic_obj.object_id )

    assert obj.object_id == basic_obj.object_id
    assert obj.revision.replace( tzinfo = utc ) == original_revision
    assert obj.value == basic_obj.value

  def test_execute_without_commit( self ):
    basic_obj = Stub_object( object_id = "5", value = 1 )
    original_revision = basic_obj.revision

    self.database.execute( basic_obj.sql_create(), commit = False )
    self.connection.rollback()
    obj = self.database.load( Stub_object, basic_obj.object_id )

    assert obj == None

  def test_execute_with_explicit_commit( self ):
    basic_obj = Stub_object( object_id = "5", value = 1 )
    original_revision = basic_obj.revision

    self.database.execute( basic_obj.sql_create(), commit = False )
    self.database.commit()
    obj = self.database.load( Stub_object, basic_obj.object_id )

    assert obj.object_id == basic_obj.object_id
    assert obj.revision.replace( tzinfo = utc ) == original_revision
    assert obj.value == basic_obj.value

  def test_load_unknown( self ):
    basic_obj = Stub_object( object_id = "5", value = 1 )
    obj = self.database.load( Stub_object, basic_obj.object_id )

    assert obj == None

  def test_next_id( self ):
    next_id = self.database.next_id( Stub_object )
    assert next_id
    assert self.database.load( Stub_object, next_id )
    prev_ids = [ next_id ]

    next_id = self.database.next_id( Stub_object )
    assert next_id
    assert next_id not in prev_ids
    assert self.database.load( Stub_object, next_id )
    prev_ids.append( next_id )

    next_id = self.database.next_id( Stub_object )
    assert next_id
    assert next_id not in prev_ids
    assert self.database.load( Stub_object, next_id )

  def test_next_id_without_commit( self ):
    next_id = self.database.next_id( Stub_object, commit = False )
    self.connection.rollback()
    assert self.database.load( Stub_object, next_id ) == None

  def test_next_id_with_explit_commit( self ):
    next_id = self.database.next_id( Stub_object, commit = False )
    self.database.commit()
    assert next_id
    assert self.database.load( Stub_object, next_id )

  def test_backend( self ):
    assert self.database.backend == Database.SQLITE_BACKEND
