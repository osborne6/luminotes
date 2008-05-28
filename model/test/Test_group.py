from pytz import utc
from datetime import datetime, timedelta
from model.Group import Group


class Test_group( object ):
  def setUp( self ):
    self.object_id = "17"
    self.name = u"my group"
    self.delta = timedelta( seconds = 1 )
    self.admin = True

    self.group = Group.create( self.object_id, self.name, self.admin )

  def test_create( self ):
    assert self.group.object_id == self.object_id
    assert datetime.now( tz = utc ) - self.group.revision < self.delta
    assert self.group.name == self.name
    assert self.group.admin == True

  def test_set_name( self ):
    new_name = u"my new group"
    previous_revision = self.group.revision
    self.group.name = new_name

    assert self.group.name == new_name
    assert self.group.revision > previous_revision

  def test_set_admin( self ):
    original_revision = self.group.revision
    self.group.admin = True

    assert self.group.admin == True
    assert self.group.revision == original_revision

  def test_to_dict( self ):
    d = self.group.to_dict()

    assert d.get( "name" ) == self.name
    assert d.get( "admin" ) == True
    assert d.get( "object_id" ) == self.group.object_id
    assert datetime.now( tz = utc ) - d.get( "revision" ) < self.delta
