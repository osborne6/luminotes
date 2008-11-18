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
    self.read_write = Notebook.READ_WRITE
    self.owner = False
    self.rank = 17.5

    self.trash = Notebook.create( self.trash_id, self.trash_name, read_write = Notebook.READ_ONLY, deleted = False, user_id = self.user_id )
    self.notebook = Notebook.create( self.object_id, self.name, trash_id = self.trash.object_id, deleted = False, user_id = self.user_id, read_write = self.read_write, owner = self.owner, rank = self.rank )
    self.note = Note.create( "19", u"<h3>title</h3>blah" )

  def test_create( self ):
    assert self.notebook.object_id == self.object_id
    assert datetime.now( tz = utc ) - self.notebook.revision < self.delta
    assert self.notebook.name == self.name
    assert self.notebook.trash_id == self.trash_id
    assert self.notebook.deleted == False
    assert self.notebook.user_id == self.user_id
    assert self.notebook.read_write == self.read_write
    assert self.notebook.owner == self.owner
    assert self.notebook.rank == self.rank
    assert self.notebook.tags == []
    assert self.notebook.note_count == None

    assert self.trash.object_id == self.trash_id
    assert datetime.now( tz = utc ) - self.trash.revision < self.delta
    assert self.trash.name == self.trash_name
    assert self.trash.trash_id == None
    assert self.trash.deleted == False
    assert self.trash.user_id == self.user_id
    assert self.trash.read_write == Notebook.READ_ONLY
    assert self.trash.owner == True
    assert self.trash.rank == None
    assert self.trash.tags == []
    assert self.trash.note_count == None

  def test_create_read_write_true( self ):
    notebook = Notebook.create( self.object_id, self.name, trash_id = None, deleted = False, user_id = self.user_id, read_write = True, owner = self.owner, rank = self.rank )

    assert notebook.object_id == self.object_id
    assert datetime.now( tz = utc ) - notebook.revision < self.delta
    assert notebook.name == self.name
    assert notebook.trash_id == None
    assert notebook.deleted == False
    assert notebook.user_id == self.user_id
    assert notebook.read_write == Notebook.READ_WRITE
    assert notebook.owner == self.owner
    assert notebook.rank == self.rank
    assert notebook.tags == []
    assert notebook.note_count == None

  def test_create_read_write_false( self ):
    notebook = Notebook.create( self.object_id, self.name, trash_id = None, deleted = False, user_id = self.user_id, read_write = False, owner = self.owner, rank = self.rank )

    assert notebook.object_id == self.object_id
    assert datetime.now( tz = utc ) - notebook.revision < self.delta
    assert notebook.name == self.name
    assert notebook.trash_id == None
    assert notebook.deleted == False
    assert notebook.user_id == self.user_id
    assert notebook.read_write == Notebook.READ_ONLY
    assert notebook.owner == self.owner
    assert notebook.rank == self.rank
    assert notebook.tags == []
    assert notebook.note_count == None

  def test_create_read_write_none( self ):
    notebook = Notebook.create( self.object_id, self.name, trash_id = None, deleted = False, user_id = self.user_id, read_write = None, owner = self.owner, rank = self.rank )

    assert notebook.object_id == self.object_id
    assert datetime.now( tz = utc ) - notebook.revision < self.delta
    assert notebook.name == self.name
    assert notebook.trash_id == None
    assert notebook.deleted == False
    assert notebook.user_id == self.user_id
    assert notebook.read_write == Notebook.READ_WRITE
    assert notebook.owner == self.owner
    assert notebook.rank == self.rank
    assert notebook.tags == []
    assert notebook.note_count == None

  def test_create_read_write_true_and_own_notes_only_true( self ):
    notebook = Notebook.create( self.object_id, self.name, trash_id = None, deleted = False, user_id = self.user_id, read_write = True, owner = self.owner, rank = self.rank, own_notes_only = True )

    assert notebook.object_id == self.object_id
    assert datetime.now( tz = utc ) - notebook.revision < self.delta
    assert notebook.name == self.name
    assert notebook.trash_id == None
    assert notebook.deleted == False
    assert notebook.user_id == self.user_id
    assert notebook.read_write == Notebook.READ_WRITE_FOR_OWN_NOTES
    assert notebook.owner == self.owner
    assert notebook.rank == self.rank
    assert notebook.tags == []
    assert notebook.note_count == None

  def test_create_read_write_false_and_own_notes_only_true( self ):
    notebook = Notebook.create( self.object_id, self.name, trash_id = None, deleted = False, user_id = self.user_id, read_write = False, owner = self.owner, rank = self.rank, own_notes_only = True )

    assert notebook.object_id == self.object_id
    assert datetime.now( tz = utc ) - notebook.revision < self.delta
    assert notebook.name == self.name
    assert notebook.trash_id == None
    assert notebook.deleted == False
    assert notebook.user_id == self.user_id
    assert notebook.read_write == Notebook.READ_ONLY
    assert notebook.owner == self.owner
    assert notebook.rank == self.rank
    assert notebook.tags == []
    assert notebook.note_count == None

  def test_create_read_write_false_and_own_notes_only_false( self ):
    notebook = Notebook.create( self.object_id, self.name, trash_id = None, deleted = False, user_id = self.user_id, read_write = False, owner = self.owner, rank = self.rank, own_notes_only = False )

    assert notebook.object_id == self.object_id
    assert datetime.now( tz = utc ) - notebook.revision < self.delta
    assert notebook.name == self.name
    assert notebook.trash_id == None
    assert notebook.deleted == False
    assert notebook.user_id == self.user_id
    assert notebook.read_write == Notebook.READ_ONLY
    assert notebook.owner == self.owner
    assert notebook.rank == self.rank
    assert notebook.tags == []
    assert notebook.note_count == None

  def test_create_read_write_true_and_own_notes_only_false( self ):
    notebook = Notebook.create( self.object_id, self.name, trash_id = None, deleted = False, user_id = self.user_id, read_write = True, owner = self.owner, rank = self.rank, own_notes_only = False )

    assert notebook.object_id == self.object_id
    assert datetime.now( tz = utc ) - notebook.revision < self.delta
    assert notebook.name == self.name
    assert notebook.trash_id == None
    assert notebook.deleted == False
    assert notebook.user_id == self.user_id
    assert notebook.read_write == Notebook.READ_WRITE
    assert notebook.owner == self.owner
    assert notebook.rank == self.rank
    assert notebook.tags == []
    assert notebook.note_count == None

  def test_create_with_note_count( self ):
    notebook = Notebook.create( self.object_id, self.name, trash_id = None, deleted = False, user_id = self.user_id, read_write = True, owner = self.owner, rank = self.rank, note_count = 7 )

    assert notebook.object_id == self.object_id
    assert datetime.now( tz = utc ) - notebook.revision < self.delta
    assert notebook.name == self.name
    assert notebook.trash_id == None
    assert notebook.deleted == False
    assert notebook.user_id == self.user_id
    assert notebook.read_write == Notebook.READ_WRITE
    assert notebook.owner == self.owner
    assert notebook.rank == self.rank
    assert notebook.tags == []
    assert notebook.note_count == 7

  def test_set_name( self ):
    new_name = u"my new notebook"
    previous_revision = self.notebook.revision
    self.notebook.name = new_name

    assert self.notebook.name == new_name
    assert self.notebook.revision > previous_revision

  def test_set_read_write( self ):
    original_revision = self.notebook.revision
    self.notebook.read_write = Notebook.READ_WRITE_FOR_OWN_NOTES

    assert self.notebook.read_write == Notebook.READ_WRITE_FOR_OWN_NOTES
    assert self.notebook.revision == original_revision

  def test_set_read_write_true( self ):
    original_revision = self.notebook.revision
    self.notebook.read_write = True

    assert self.notebook.read_write == Notebook.READ_WRITE
    assert self.notebook.revision == original_revision

  def test_set_read_write_false( self ):
    original_revision = self.notebook.revision
    self.notebook.read_write = False

    assert self.notebook.read_write == Notebook.READ_ONLY
    assert self.notebook.revision == original_revision

  def test_set_read_write_none( self ):
    original_revision = self.notebook.revision
    self.notebook.read_write = None

    assert self.notebook.read_write == Notebook.READ_WRITE
    assert self.notebook.revision == original_revision

  def test_set_deleted( self ):
    previous_revision = self.notebook.revision
    self.notebook.deleted = True

    assert self.notebook.deleted == True
    assert self.notebook.revision > previous_revision

  def test_set_user_id( self ):
    previous_revision = self.notebook.revision
    self.notebook.user_id = u"5"

    assert self.notebook.user_id == u"5"
    assert self.notebook.revision > previous_revision

  def test_set_rank( self ):
    original_revision = self.notebook.revision
    self.notebook.rank = 17.7

    assert self.notebook.rank == 17.7
    assert self.notebook.revision == original_revision

  def test_set_tags( self ):
    original_revision = self.notebook.revision
    self.notebook.tags = [ u"whee", u"blah", u"hm" ] # normally these would be Tag objects

    assert self.notebook.tags == [ u"whee", u"blah", u"hm" ]
    assert self.notebook.revision == original_revision

  def test_to_dict( self ):
    d = self.notebook.to_dict()

    assert d.get( "name" ) == self.name
    assert d.get( "trash_id" ) == self.trash.object_id
    assert d.get( "read_write" ) == self.read_write
    assert d.get( "deleted" ) == self.notebook.deleted
    assert d.get( "user_id" ) == self.notebook.user_id
    assert d.get( "note_count" ) == self.notebook.note_count
    assert d.get( "object_id" ) == self.notebook.object_id
    assert datetime.now( tz = utc ) - d.get( "revision" ) < self.delta
    assert d.get( "tags" ) == []
