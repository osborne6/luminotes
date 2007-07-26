from datetime import datetime, timedelta
from model.Persistent import Persistent


class Test_persistent( object ):
  def setUp( self ):
    self.object_id = "17"
    self.obj = Persistent( self.object_id )
    self.delta = timedelta( seconds = 1 )

  def test_create( self ):
    assert self.obj.object_id == self.object_id
    assert self.obj.secondary_id == None
    assert datetime.now() - self.obj.revision < self.delta

  def test_revision_id( self ):
    assert self.obj.revision_id() == "%s %s" % ( self.object_id, self.obj.revision )

  def test_make_revision_id( self ):
    assert self.obj.revision_id() == Persistent.make_revision_id( self.object_id, self.obj.revision )

  def test_update_revision( self ):
    previous_revision = self.obj.revision
    self.obj.update_revision()
    assert self.obj.revision > previous_revision
    assert datetime.now() - self.obj.revision < self.delta

    previous_revision = self.obj.revision
    self.obj.update_revision()
    assert self.obj.revision > previous_revision
    assert datetime.now() - self.obj.revision < self.delta

  def test_to_dict( self ):
    d = self.obj.to_dict()

    assert d.get( "object_id" ) == self.object_id
    assert d.get( "revision" ) == self.obj.revision
    assert d.get( "revisions_list" ) == self.obj.revisions_list


class Test_persistent_with_secondary_id( object ):
  def setUp( self ):
    self.object_id = "17"
    self.secondary_id = u"foo"
    self.obj = Persistent( self.object_id, self.secondary_id )
    self.delta = timedelta( seconds = 1 )

  def test_create( self ):
    assert self.obj.object_id == self.object_id
    assert self.obj.secondary_id == self.secondary_id
    assert datetime.now() - self.obj.revision < self.delta
