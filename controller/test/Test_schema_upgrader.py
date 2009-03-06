import re
from nose.tools import raises
from pysqlite2 import dbapi2 as sqlite
from Stub_object import Stub_object
from Stub_cache import Stub_cache
from model.Persistent import Persistent
from controller.Database import Database, Connection_wrapper
from controller.Schema_upgrader import Schema_upgrader


class Test_schema_upgrader( object ):
  def setUp( self ):
    # make an in-memory sqlite database to use during testing
    self.connection = Connection_wrapper( sqlite.connect( ":memory:", detect_types = sqlite.PARSE_DECLTYPES, check_same_thread = False ) )
    self.cache = Stub_cache()
    cursor = self.connection.cursor()
    cursor.execute( Stub_object.sql_create_table() )

    self.fake_files = {} # map of fake filename (full path) to fake file contents
    self.database = Database( self.connection, self.cache )
    self.upgrader = Schema_upgrader( self.database, glob = self.glob, read_file = self.read_file )

  def tearDown( self ):
    self.database.close()

  def glob( self, glob_pattern ):
    """
    A fake glob function that doesn't use the filesystem.
    """
    re_pattern = re.compile( glob_pattern.replace( "*", "[^/]*" ) )

    return [ filename for filename in self.fake_files.keys() if re_pattern.search( filename ) ]

  def read_file( self, filename ):
    """
    A fake read file function that doesn't use the filesystem.
    """
    contents = self.fake_files.get( filename )

    if not contents:
      raise IOError()

    return contents

  def test_upgrade_schema( self ):
    self.fake_files = {
      u"model/delta/5.6.7.sqlite": u"create table new_table ( foo text ); insert into new_table values ( 'hi' );",
      u"model/delta/5.6.8.sqlite": u"insert into new_table values ( 'bye' );",
      u"model/delta/5.6.10.sqlite": u"alter table new_table add column bar text;",
      u"model/delta/5.7.11.sqlite": u"insert into new_table values ( 'whee', 'stuff' );",
      u"model/delta/5.7.18.sqlite": u"insert into new_table values ( 'should not be present', 'nope' );",
    }

    self.upgrader.upgrade_schema( u"5.7.11" )

    result = self.database.select_many( tuple, u"select * from new_table;" )
    assert result == [ ( u"hi", None ), ( u"bye", None ), ( "whee", "stuff" ) ]

    result = self.database.select_many( tuple, u"select * from schema_version;" )
    assert result == [ ( 5, 7, 11 ) ]

  def test_upgrade_schema_with_schema_version_table( self ):
    self.database.execute( u"create table schema_version ( major numeric, minor numeric, \"release\" numeric );" )
    self.database.execute( u"insert into schema_version values ( 0, 0, 0 );" )
    self.test_upgrade_schema()

  def test_upgrade_schema_with_schema_version_table_and_specific_starting_version( self ):
    self.database.execute( u"create table schema_version ( major numeric, minor numeric, \"release\" numeric );" )
    self.database.execute( u"insert into schema_version values ( 5, 6, 6 );" )

    self.fake_files[ u"model/delta/5.6.1.sqlite" ] = u"this is not valid sql and should not be executed anyway;"
    self.fake_files[ u"model/delta/5.6.6.sqlite" ] = u"also invalid;"

    self.test_upgrade_schema()

  def test_upgrade_schema_with_future_ending_version( self ):
    self.fake_files = {
      u"model/delta/5.6.7.sqlite": u"create table new_table ( foo text ); insert into new_table values ( 'hi' );",
      u"model/delta/5.6.8.sqlite": u"insert into new_table values ( 'bye' );",
      u"model/delta/5.6.10.sqlite": u"alter table new_table add column bar text;",
      u"model/delta/5.7.11.sqlite": u"insert into new_table values ( 'whee', 'stuff' );",
      u"model/delta/5.7.18.sqlite": u"insert into new_table values ( 'more', 'and more' );",
    }

    self.upgrader.upgrade_schema( u"5.8.55" )

    result = self.database.select_many( tuple, u"select * from new_table;" )
    assert result == [ ( u"hi", None ), ( u"bye", None ), ( "whee", "stuff" ), ( "more", "and more" ) ]

    result = self.database.select_many( tuple, u"select * from schema_version;" )
    assert result == [ ( 5, 7, 18 ) ]

  def test_upgrade_schema_twice( self ):
    self.test_upgrade_schema()

    # the second upgrade should have no effect, because at this point it's already upgraded
    self.test_upgrade_schema()

  def test_upgrade_schema_with_filename_with_invalid_version( self ):
    # the filename, not composed of all-integer parts, should be skipped
    self.fake_files[ u"model/delta/5.6.9b.sqlite" ] = u"this is not valid sql and should not be executed anyway;"

    self.test_upgrade_schema()

  def test_upgrade_schema_default_to_start_version_of_1_5_4( self ):
    # test that if no schema_version table exists, then the starting version is assumed to be 1.5.4
    self.fake_files = {
      u"model/delta/1.5.3.sqlite": u"invalid sql;",
      u"model/delta/1.5.4.sqlite": u"should not be invoked;",
      u"model/delta/1.5.5.sqlite": u"create table new_table ( foo text ); insert into new_table values ( 'hi' );",
      u"model/delta/1.5.6.sqlite": u"insert into new_table values ( 'bye' );",
    }

    self.upgrader.upgrade_schema( u"1.5.6" )

    result = self.database.select_many( tuple, u"select * from new_table;" )
    assert result == [ ( u"hi", ), ( u"bye", ), ]

    result = self.database.select_many( tuple, u"select * from schema_version;" )
    assert result == [ ( 1, 5, 6 ) ]

  def test_apply_schema_delta( self ):
    self.database.execute( u"create table schema_version ( major numeric, minor numeric, \"release\" numeric );" )
    self.database.execute( u"insert into schema_version values ( 0, 0, 0 );" )

    self.fake_files = {
      u"model/delta/5.6.5.sqlite": u"insert into new_table values ( 'should not show up' );",
      u"model/delta/5.6.7.sqlite": u"create table new_table ( foo text ); insert into new_table values ( 'hi' );",
      u"model/delta/5.7.18.sqlite": u"insert into new_table values ( 'should not be present' );",
    }

    self.upgrader.apply_schema_delta( ( 5, 6, 7 ), u"model/delta/5.6.7.sqlite" )

    result = self.database.select_many( unicode, u"select * from new_table;" );
    assert result == [ u"hi" ]

    result = self.database.select_many( tuple, u"select * from schema_version;" );
    assert result == [ ( 5, 6, 7 ) ]

  @raises( IOError )
  def test_apply_schema_delta_with_unknown_file( self ):
    self.upgrader.apply_schema_delta( ( 5, 6, 7 ), u"model/delta/5.6.7.sqlite" )

  def test_version_string_to_tuple( self ):
    version = self.upgrader.version_string_to_tuple( "2.5.13" )

    assert len( version ) == 3
    assert version[ 0 ] == 2
    assert version[ 1 ] == 5
    assert version[ 2 ] == 13

  def test_version_string_to_tuple_with_extension( self ):
    version = self.upgrader.version_string_to_tuple( "2.5.13.sqlite" )

    assert len( version ) == 3
    assert version[ 0 ] == 2
    assert version[ 1 ] == 5
    assert version[ 2 ] == 13

  @raises( ValueError )
  def test_version_string_to_tuple_with_too_many_parts( self ):
    version = self.upgrader.version_string_to_tuple( "3.14.159.26.5" )

  @raises( ValueError )
  def test_version_string_to_tuple_with_too_few_parts( self ):
    version = self.upgrader.version_string_to_tuple( "3.14" )

  @raises( ValueError )
  def test_version_string_to_tuple_with_non_integer_part( self ):
    version = self.upgrader.version_string_to_tuple( "2.5b.13" )

  @raises( ValueError )
  def test_version_string_to_tuple_with_empty_part( self ):
    version = self.upgrader.version_string_to_tuple( "2..13" )
