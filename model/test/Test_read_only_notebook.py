from nose.tools import raises
from model.Notebook import Notebook
from model.Read_only_notebook import Read_only_notebook
from model.Entry import Entry


class Test_read_only_notebook( object ):
  def setUp( self ):
    self.object_id = "17"
    self.read_only_id = "22"
    self.name = u"my notebook"

    self.notebook = Notebook( self.object_id, self.name )
    self.entry = Entry( "18", u"<h3>title</h3>blah" )
    self.notebook.add_entry( self.entry )
    self.notebook.add_startup_entry( self.entry )

    self.read_only = Read_only_notebook( self.read_only_id, self.notebook )

  def test_create( self ):
    assert self.read_only.object_id == self.read_only_id
    assert self.read_only.name == self.name
    assert self.read_only.entries == [ self.entry ]
    assert self.read_only.startup_entries == [ self.entry ]

  @raises( AttributeError )
  def test_set_name( self ):
    self.read_only.name = u"my new notebook"

  @raises( AttributeError )
  def test_add_entry( self ):
    self.read_only.add_entry( self.entry )

  def test_lookup_entry( self ):
    entry = self.read_only.lookup_entry( self.entry.object_id ) 
    assert entry == self.entry

  def test_lookup_unknown_entry( self ):
    entry = self.read_only.lookup_entry( "55" )
    assert entry == None

  def test_lookup_entry_by_title( self ):
    entry = self.read_only.lookup_entry_by_title( self.entry.title )
    assert entry == self.entry

  def test_lookup_unknown_entry_by_title( self ):
    entry = self.read_only.lookup_entry( self.entry.title )
    assert entry == None

  @raises( AttributeError )
  def test_remove_entry( self ):
    self.read_only.remove_entry( self.entry )

  @raises( AttributeError )
  def test_update_entry( self ):
    new_title = u"new title"
    new_contents = u"<h3>%s</h3>new blah" % new_title
    self.read_only.update_entry( self.entry, new_contents )

  @raises( AttributeError )
  def test_add_startup_entry( self ):
    self.read_only.add_startup_entry( self.entry )

  @raises( AttributeError )
  def test_remove_startup_entry( self ):
    self.read_only.remove_startup_entry( self.entry )

  def test_to_dict( self ):
    d = self.read_only.to_dict()

    assert d.get( "object_id" ) == self.read_only_id
    assert d.get( "name" ) == self.name
    assert d.get( "read_write" ) == False
