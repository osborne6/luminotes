from pytz import utc
from datetime import datetime, timedelta
from model.Persistent import Persistent, quote


class Test_persistent( object ):
  def setUp( self ):
    self.object_id = "17"
    self.obj = Persistent( self.object_id )
    self.delta = timedelta( seconds = 1 )

  def test_create( self ):
    assert self.obj.object_id == self.object_id
    assert datetime.now( tz = utc ) - self.obj.revision < self.delta

  def test_update_revision( self ):
    previous_revision = self.obj.revision
    self.obj.update_revision()
    assert self.obj.revision > previous_revision
    assert datetime.now( tz = utc ) - self.obj.revision < self.delta

    previous_revision = self.obj.revision
    self.obj.update_revision()
    assert self.obj.revision > previous_revision
    assert datetime.now( tz = utc ) - self.obj.revision < self.delta

  def test_to_dict( self ):
    d = self.obj.to_dict()

    assert d.get( "object_id" ) == self.object_id
    assert d.get( "revision" ) == self.obj.revision


class Test_persistent_with_revision( object ):
  def setUp( self ):
    self.object_id = "17"
    self.revision = datetime.now( tz = utc ) - timedelta( hours = 24 )
    self.obj = Persistent( self.object_id, self.revision )
    self.delta = timedelta( seconds = 1 )

  def test_create( self ):
    assert self.obj.object_id == self.object_id
    assert self.revision - self.obj.revision < self.delta

  def test_update_revision( self ):
    previous_revision = self.obj.revision
    self.obj.update_revision()
    assert self.obj.revision > previous_revision
    assert datetime.now( tz = utc ) - self.obj.revision < self.delta

    previous_revision = self.obj.revision
    self.obj.update_revision()
    assert self.obj.revision > previous_revision
    assert datetime.now( tz = utc ) - self.obj.revision < self.delta

  def test_to_dict( self ):
    d = self.obj.to_dict()

    assert d.get( "object_id" ) == self.object_id
    assert d.get( "revision" ) == self.obj.revision


def test_quote():
  assert "'foo'" == quote( "foo" )

def test_quote_apostrophe():
  assert "'it''s'" == quote( "it's" )

def test_quote_backslash():
  assert r"'c:\\\\whee'" == quote( r"c:\\whee" )

def test_quote_none():
  assert "null" == quote( None )
