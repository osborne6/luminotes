from pytz import utc
from datetime import datetime, timedelta
from model.File import File


class Test_file( object ):
  def setUp( self ):
    self.object_id = u"17"
    self.notebook_id = u"18"
    self.note_id = u"19"
    self.filename = u"foo.png"
    self.size_bytes = 2888
    self.content_type = "image/png"
    self.delta = timedelta( seconds = 1 )

    self.file = File.create( self.object_id, self.notebook_id, self.note_id, self.filename,
                             self.size_bytes, self.content_type )

  def test_create( self ):
    assert self.file.object_id == self.object_id
    assert self.file.notebook_id == self.notebook_id
    assert self.file.note_id == self.note_id
    assert self.file.filename == self.filename
    assert self.file.size_bytes == self.size_bytes
    assert self.file.content_type == self.content_type

  def test_to_dict( self ):
    d = self.file.to_dict()

    assert d.get( "object_id" ) == self.object_id
    assert datetime.now( tz = utc ) - d.get( "revision" ) < self.delta
    assert d.get( "notebook_id" ) == self.notebook_id
    assert d.get( "note_id" ) == self.note_id
    assert d.get( "filename" ) == self.filename
    assert d.get( "size_bytes" ) == self.size_bytes
    assert d.get( "content_type" ) == self.content_type
