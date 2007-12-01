from pytz import utc
from datetime import datetime, timedelta
from model.Notebook import Notebook
from model.Note import Note


class Test_notebook( object ):
  def setUp( self ):
    self.object_id = "17"
    self.trash_id = "18"
    self.name = u"my notebook"
    self.trash_name = u"trash"
    self.user_id = u"me"
    self.delta = timedelta( seconds = 1 )

    self.trash = Notebook.create( self.trash_id, self.trash_name, read_write = False, deleted = False, user_id = self.user_id )
    self.notebook = Notebook.create( self.object_id, self.name, trash_id = self.trash.object_id, deleted = False, user_id = self.user_id )
    self.note = Note.create( "19", u"<h3>title</h3>blah" )

  def test_create( self ):
    assert self.notebook.object_id == self.object_id
    assert datetime.now( tz = utc ) - self.notebook.revision < self.delta
    assert self.notebook.name == self.name
    assert self.notebook.read_write == True
    assert self.notebook.trash_id == self.trash_id
    assert self.notebook.deleted == False
    assert self.notebook.user_id == self.user_id

    assert self.trash.object_id == self.trash_id
    assert datetime.now( tz = utc ) - self.trash.revision < self.delta
    assert self.trash.name == self.trash_name
    assert self.trash.read_write == False
    assert self.trash.trash_id == None
    assert self.trash.deleted == False
    assert self.trash.user_id == self.user_id

  def test_set_name( self ):
    new_name = u"my new notebook"
    previous_revision = self.notebook.revision
    self.notebook.name = new_name

    assert self.notebook.name == new_name
    assert self.notebook.revision > previous_revision

  def test_set_read_write( self ):
    original_revision = self.notebook.revision
    self.notebook.read_write = True

    assert self.notebook.read_write == True
    assert self.notebook.revision == original_revision

  def test_set_deleted( self ):
    previous_revision = self.notebook.revision
    self.notebook.deleted = True

    assert self.notebook.deleted == True
    assert self.notebook.revision > previous_revision

  def test_to_dict( self ):
    d = self.notebook.to_dict()

    assert d.get( "name" ) == self.name
    assert d.get( "trash_id" ) == self.trash.object_id
    assert d.get( "read_write" ) == True
    assert d.get( "deleted" ) == self.notebook.deleted
    assert d.get( "user_id" ) == self.notebook.user_id
    assert d.get( "object_id" ) == self.notebook.object_id
    assert datetime.now( tz = utc ) - d.get( "revision" ) < self.delta
