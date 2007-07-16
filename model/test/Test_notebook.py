from nose.tools import raises
from model.Notebook import Notebook
from model.Entry import Entry


class Test_notebook( object ):
  def setUp( self ):
    self.object_id = 17
    self.name = u"my notebook"

    self.notebook = Notebook( self.object_id, self.name )
    self.entry = Entry( 18, u"<h3>title</h3>blah" )

  def test_create( self ):
    assert self.notebook.object_id == self.object_id
    assert self.notebook.name == self.name

  def test_set_name( self ):
    new_name = u"my new notebook"
    previous_revision = self.notebook.revision
    self.notebook.name = new_name

    assert self.notebook.name == new_name
    assert self.notebook.revision > previous_revision

  def test_add_and_lookup_entry( self ):
    previous_revision = self.notebook.revision
    self.notebook.add_entry( self.entry )
    assert self.notebook.revision > previous_revision

    entry = self.notebook.lookup_entry( self.entry.object_id ) 
    assert entry == self.entry

  def test_lookup_unknown_entry( self ):
    entry = self.notebook.lookup_entry( self.entry.object_id )
    assert entry == None

  def test_add_and_lookup_entry_by_title( self ):
    previous_revision = self.notebook.revision
    self.notebook.add_entry( self.entry )
    assert self.notebook.revision > previous_revision

    entry = self.notebook.lookup_entry_by_title( self.entry.title )
    assert entry == self.entry

  def test_lookup_unknown_entry_by_title( self ):
    entry = self.notebook.lookup_entry( self.entry.title )
    assert entry == None

  def test_remove_entry( self ):
    previous_revision = self.notebook.revision
    self.notebook.add_entry( self.entry )
    result = self.notebook.remove_entry( self.entry )
    assert result == True
    assert self.notebook.revision > previous_revision

    entry = self.notebook.lookup_entry( self.entry.object_id )
    assert entry == None

    entry = self.notebook.lookup_entry_by_title( self.entry.title )
    assert entry == None

    assert not entry in self.notebook.startup_entries

  def test_remove_unknown_entry( self ):
    revision = self.notebook.revision
    result = self.notebook.remove_entry( self.entry )
    assert result == False
    assert self.notebook.revision == revision

    entry = self.notebook.lookup_entry( self.entry.object_id )
    assert entry == None

  def test_update_entry( self ):
    self.notebook.add_entry( self.entry )
    old_title = self.entry.title

    new_title = u"new title"
    new_contents = u"<h3>%s</h3>new blah" % new_title
    previous_revision = self.notebook.revision
    self.notebook.update_entry( self.entry, new_contents )

    assert self.entry.contents == new_contents
    assert self.entry.title == new_title
    assert self.notebook.revision > previous_revision

    entry = self.notebook.lookup_entry( self.entry.object_id )
    assert entry == self.entry

    entry = self.notebook.lookup_entry_by_title( old_title )
    assert entry == None

    entry = self.notebook.lookup_entry_by_title( new_title )
    assert entry == self.entry

  def test_update_unrevised_entry( self ):
    self.notebook.add_entry( self.entry )
    old_title = self.entry.title

    revision = self.notebook.revision
    self.notebook.update_entry( self.entry, self.entry.contents )
    assert self.notebook.revision == revision

    entry = self.notebook.lookup_entry( self.entry.object_id )
    assert entry == self.entry

  @raises( Notebook.UnknownEntryError )
  def test_update_unknown_entry( self ):
    new_contents = u"<h3>new title</h3>new blah"
    self.notebook.update_entry( self.entry, new_contents )

  def test_add_startup_entry( self ):
    self.notebook.add_entry( self.entry )

    previous_revision = self.notebook.revision
    self.notebook.add_startup_entry( self.entry )

    assert self.entry in self.notebook.startup_entries
    assert self.notebook.revision > previous_revision

  def test_add_duplicate_startup_entry( self ):
    self.notebook.add_entry( self.entry )

    previous_revision = self.notebook.revision
    self.notebook.add_startup_entry( self.entry )

    assert self.entry in self.notebook.startup_entries
    assert self.notebook.revision > previous_revision

    revision = self.notebook.revision
    self.notebook.add_startup_entry( self.entry )

    assert self.notebook.startup_entries.count( self.entry ) == 1
    assert self.notebook.revision == revision

  @raises( Notebook.UnknownEntryError )
  def test_add_unknown_startup_entry( self ):
    self.notebook.add_startup_entry( self.entry )

  def test_remove_startup_entry( self ):
    self.notebook.add_entry( self.entry )
    self.notebook.add_startup_entry( self.entry )

    previous_revision = self.notebook.revision
    result = self.notebook.remove_startup_entry( self.entry )

    assert result == True
    assert not self.entry in self.notebook.startup_entries
    assert self.notebook.revision > previous_revision

  def test_remove_unknown_startup_entry( self ):
    self.notebook.add_entry( self.entry )

    revision = self.notebook.revision
    result = self.notebook.remove_startup_entry( self.entry )

    assert result == False
    assert not self.entry in self.notebook.startup_entries
    assert self.notebook.revision == revision

  def test_to_dict( self ):
    d = self.notebook.to_dict()

    assert d.get( "name" ) == self.name
    assert d.get( "startup_entries" ) == []
    assert d.get( "read_write" ) == True

  def test_to_dict_with_startup_entries( self ):
    self.notebook.add_entry( self.entry )
    self.notebook.add_startup_entry( self.entry )

    d = self.notebook.to_dict()

    assert d.get( "name" ) == self.name
    assert d.get( "startup_entries" ) == [ self.entry ]
    assert d.get( "read_write" ) == True
