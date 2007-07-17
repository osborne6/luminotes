from nose.tools import raises
from model.Notebook import Notebook
from model.Read_only_notebook import Read_only_notebook
from model.Note import Note


class Test_read_only_notebook( object ):
  def setUp( self ):
    self.object_id = "17"
    self.read_only_id = "22"
    self.name = u"my notebook"

    self.notebook = Notebook( self.object_id, self.name )
    self.note = Note( "18", u"<h3>title</h3>blah" )
    self.notebook.add_note( self.note )
    self.notebook.add_startup_note( self.note )

    self.read_only = Read_only_notebook( self.read_only_id, self.notebook )

  def test_create( self ):
    assert self.read_only.object_id == self.read_only_id
    assert self.read_only.name == self.name
    assert self.read_only.notes == [ self.note ]
    assert self.read_only.startup_notes == [ self.note ]

  @raises( AttributeError )
  def test_set_name( self ):
    self.read_only.name = u"my new notebook"

  @raises( AttributeError )
  def test_add_note( self ):
    self.read_only.add_note( self.note )

  def test_lookup_note( self ):
    note = self.read_only.lookup_note( self.note.object_id ) 
    assert note == self.note

  def test_lookup_unknown_note( self ):
    note = self.read_only.lookup_note( "55" )
    assert note == None

  def test_lookup_note_by_title( self ):
    note = self.read_only.lookup_note_by_title( self.note.title )
    assert note == self.note

  def test_lookup_unknown_note_by_title( self ):
    note = self.read_only.lookup_note( self.note.title )
    assert note == None

  @raises( AttributeError )
  def test_remove_note( self ):
    self.read_only.remove_note( self.note )

  @raises( AttributeError )
  def test_update_note( self ):
    new_title = u"new title"
    new_contents = u"<h3>%s</h3>new blah" % new_title
    self.read_only.update_note( self.note, new_contents )

  @raises( AttributeError )
  def test_add_startup_note( self ):
    self.read_only.add_startup_note( self.note )

  @raises( AttributeError )
  def test_remove_startup_note( self ):
    self.read_only.remove_startup_note( self.note )

  def test_to_dict( self ):
    d = self.read_only.to_dict()

    assert d.get( "object_id" ) == self.read_only_id
    assert d.get( "name" ) == self.name
    assert d.get( "read_write" ) == False
