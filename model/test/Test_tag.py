from pytz import utc
from datetime import datetime, timedelta
from model.Tag import Tag


class Test_tag( object ):
  def setUp( self ):
    self.object_id = u"17"
    self.notebook_id = u"19"
    self.user_id = u"20"
    self.name = u"mytag"
    self.description = u"this is my tag"
    self.value = u"a value"
    self.delta = timedelta( seconds = 1 )

    self.tag = Tag.create( self.object_id, self.notebook_id, self.user_id, self.name,
                           self.description, self.value )

  def test_create( self ):
    assert self.tag.object_id == self.object_id
    assert self.tag.notebook_id == self.notebook_id
    assert self.tag.user_id == self.user_id
    assert self.tag.name == self.name
    assert self.tag.description == self.description
    assert self.tag.value == self.value

  def test_to_dict( self ):
    d = self.tag.to_dict()

    assert d.get( "object_id" ) == self.object_id
    assert datetime.now( tz = utc ) - d.get( "revision" ) < self.delta
    assert d.get( "notebook_id" ) == self.notebook_id
    assert d.get( "user_id" ) == self.user_id
    assert d.get( "name" ) == self.name
    assert d.get( "description" ) == self.description
    assert d.get( "value" ) == self.value
