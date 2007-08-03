from nose.tools import raises
from model.Notebook import Notebook
from model.Note import Note


class Test_notebook( object ):
  def setUp( self ):
    self.object_id = "17"
    self.trash_id = "18"
    self.name = u"my notebook"
    self.trash_name = u"trash"

    self.trash = Notebook( self.trash_id, self.trash_name )
    self.notebook = Notebook( self.object_id, self.name, self.trash )
    self.note = Note( "19", u"<h3>title</h3>blah" )

  def test_create( self ):
    assert self.notebook.object_id == self.object_id
    assert self.notebook.name == self.name
    assert self.notebook.trash
    assert self.notebook.trash.object_id == self.trash_id
    assert self.notebook.trash.name == self.trash_name

  def test_set_name( self ):
    new_name = u"my new notebook"
    previous_revision = self.notebook.revision
    self.notebook.name = new_name

    assert self.notebook.name == new_name
    assert self.notebook.revision > previous_revision

  def test_add_and_lookup_note( self ):
    previous_revision = self.notebook.revision
    self.notebook.add_note( self.note )
    assert self.notebook.revision > previous_revision

    note = self.notebook.lookup_note( self.note.object_id ) 
    assert note == self.note

  def test_lookup_unknown_note( self ):
    note = self.notebook.lookup_note( self.note.object_id )
    assert note == None

  def test_add_and_lookup_note_by_title( self ):
    previous_revision = self.notebook.revision
    self.notebook.add_note( self.note )
    assert self.notebook.revision > previous_revision

    note = self.notebook.lookup_note_by_title( self.note.title )
    assert note == self.note

  def test_lookup_unknown_note_by_title( self ):
    note = self.notebook.lookup_note( self.note.title )
    assert note == None

  def test_remove_note( self ):
    previous_revision = self.notebook.revision
    self.notebook.add_note( self.note )
    result = self.notebook.remove_note( self.note )
    assert result == True
    assert self.notebook.revision > previous_revision

    note = self.notebook.lookup_note( self.note.object_id )
    assert note == None

    note = self.notebook.lookup_note_by_title( self.note.title )
    assert note == None

    assert not note in self.notebook.startup_notes

  def test_remove_unknown_note( self ):
    revision = self.notebook.revision
    result = self.notebook.remove_note( self.note )
    assert result == False
    assert self.notebook.revision == revision

    note = self.notebook.lookup_note( self.note.object_id )
    assert note == None

  def test_update_note( self ):
    self.notebook.add_note( self.note )
    old_title = self.note.title

    new_title = u"new title"
    new_contents = u"<h3>%s</h3>new blah" % new_title
    previous_revision = self.notebook.revision
    self.notebook.update_note( self.note, new_contents )

    assert self.note.contents == new_contents
    assert self.note.title == new_title
    assert self.notebook.revision > previous_revision

    note = self.notebook.lookup_note( self.note.object_id )
    assert note == self.note

    note = self.notebook.lookup_note_by_title( old_title )
    assert note == None

    note = self.notebook.lookup_note_by_title( new_title )
    assert note == self.note

  def test_update_unrevised_note( self ):
    self.notebook.add_note( self.note )
    old_title = self.note.title

    revision = self.notebook.revision
    self.notebook.update_note( self.note, self.note.contents )
    assert self.notebook.revision == revision

    note = self.notebook.lookup_note( self.note.object_id )
    assert note == self.note

  @raises( Notebook.UnknownNoteError )
  def test_update_unknown_note( self ):
    new_contents = u"<h3>new title</h3>new blah"
    self.notebook.update_note( self.note, new_contents )

  def test_add_startup_note( self ):
    self.notebook.add_note( self.note )

    previous_revision = self.notebook.revision
    self.notebook.add_startup_note( self.note )

    assert self.note in self.notebook.startup_notes
    assert self.notebook.revision > previous_revision

  def test_add_duplicate_startup_note( self ):
    self.notebook.add_note( self.note )

    previous_revision = self.notebook.revision
    self.notebook.add_startup_note( self.note )

    assert self.note in self.notebook.startup_notes
    assert self.notebook.revision > previous_revision

    revision = self.notebook.revision
    self.notebook.add_startup_note( self.note )

    assert self.notebook.startup_notes.count( self.note ) == 1
    assert self.notebook.revision == revision

  @raises( Notebook.UnknownNoteError )
  def test_add_unknown_startup_note( self ):
    self.notebook.add_startup_note( self.note )

  def test_remove_startup_note( self ):
    self.notebook.add_note( self.note )
    self.notebook.add_startup_note( self.note )

    previous_revision = self.notebook.revision
    result = self.notebook.remove_startup_note( self.note )

    assert result == True
    assert not self.note in self.notebook.startup_notes
    assert self.notebook.revision > previous_revision

  def test_remove_unknown_startup_note( self ):
    self.notebook.add_note( self.note )

    revision = self.notebook.revision
    result = self.notebook.remove_startup_note( self.note )

    assert result == False
    assert not self.note in self.notebook.startup_notes
    assert self.notebook.revision == revision

  def test_to_dict( self ):
    d = self.notebook.to_dict()

    assert d.get( "name" ) == self.name
    assert d.get( "trash" ) == self.trash
    assert d.get( "startup_notes" ) == []
    assert d.get( "read_write" ) == True

  def test_to_dict_with_startup_notes( self ):
    self.notebook.add_note( self.note )
    self.notebook.add_startup_note( self.note )

    d = self.notebook.to_dict()

    assert d.get( "name" ) == self.name
    assert d.get( "trash" ) == self.trash
    assert d.get( "startup_notes" ) == [ self.note ]
    assert d.get( "read_write" ) == True
