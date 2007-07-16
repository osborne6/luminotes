import cherrypy
import cgi
from Test_controller import Test_controller
from controller.Scheduler import Scheduler
from model.Notebook import Notebook
from model.Entry import Entry
from model.User import User


class Test_notebooks( Test_controller ):
  def setUp( self ):
    Test_controller.setUp( self )

    self.notebook = None
    self.anon_notebook = None
    self.unknown_notebook_id = "17"
    self.unknown_entry_id = "42"
    self.username = u"mulder"
    self.password = u"trustno1"
    self.email_address = u"outthere@example.com"
    self.user = None
    self.anonymous = None
    self.session_id = None

    thread = self.make_notebooks()
    self.scheduler.add( thread )
    self.scheduler.wait_for( thread )

    thread = self.make_users()
    self.scheduler.add( thread )
    self.scheduler.wait_for( thread )

  def make_notebooks( self ):
    self.database.next_id( self.scheduler.thread )
    self.notebook = Notebook( ( yield Scheduler.SLEEP ), u"notebook" )

    self.database.next_id( self.scheduler.thread )
    self.entry = Entry( ( yield Scheduler.SLEEP ), u"<h3>my title</h3>blah" )
    self.notebook.add_entry( self.entry )
    self.notebook.add_startup_entry( self.entry )

    self.database.next_id( self.scheduler.thread )
    self.entry2 = Entry( ( yield Scheduler.SLEEP ), u"<h3>other title</h3>whee" )
    self.notebook.add_entry( self.entry2 )
    self.database.save( self.notebook )

    self.database.next_id( self.scheduler.thread )
    self.anon_notebook = Notebook( ( yield Scheduler.SLEEP ), u"anon_notebook" )
    self.database.save( self.anon_notebook )

  def make_users( self ):
    self.database.next_id( self.scheduler.thread )
    self.user = User( ( yield Scheduler.SLEEP ), self.username, self.password, self.email_address, [ self.notebook ] )
    self.database.next_id( self.scheduler.thread )
    self.anonymous = User( ( yield Scheduler.SLEEP ), u"anonymous", None, None, [ self.anon_notebook ] )

    self.database.save( self.user )
    self.database.save( self.anonymous )

  def test_default( self ):
    result = self.http_get( "/notebooks/%s" % self.notebook.object_id )
    
    assert result.get( u"notebook_id" ) == self.notebook.object_id

  def test_contents( self ):
    self.login()

    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert notebook.object_id == self.notebook.object_id
    assert len( notebook.startup_entries ) == 1
    assert notebook.startup_entries[ 0 ] == self.entry

  def test_contents_without_login( self ):
    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    assert result.get( "error" )

  def test_load_entry( self ):
    self.login()

    result = self.http_post( "/notebooks/load_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.entry.object_id,
    ), session_id = self.session_id )

    entry = result[ "entry" ]

    assert entry.object_id == self.entry.object_id
    assert entry.title == self.entry.title
    assert entry.contents == self.entry.contents

  def test_load_entry_without_login( self ):
    result = self.http_post( "/notebooks/load_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.entry.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_load_entry_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/load_entry/", dict(
      notebook_id = self.unknown_notebook_id,
      entry_id = self.entry.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_load_unknown_entry( self ):
    self.login()

    result = self.http_post( "/notebooks/load_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.unknown_entry_id,
    ), session_id = self.session_id )

    entry = result[ "entry" ]
    assert entry == None

  def test_load_entry_by_title( self ):
    self.login()

    result = self.http_post( "/notebooks/load_entry_by_title/", dict(
      notebook_id = self.notebook.object_id,
      entry_title = self.entry.title,
    ), session_id = self.session_id )

    entry = result[ "entry" ]

    assert entry.object_id == self.entry.object_id
    assert entry.title == self.entry.title
    assert entry.contents == self.entry.contents

  def test_load_entry_by_title_without_login( self ):
    result = self.http_post( "/notebooks/load_entry_by_title/", dict(
      notebook_id = self.notebook.object_id,
      entry_title = self.entry.title,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_load_entry_by_title_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/load_entry_by_title/", dict(
      notebook_id = self.unknown_notebook_id,
      entry_title = self.entry.title,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_load_unknown_entry_by_title( self ):
    self.login()

    result = self.http_post( "/notebooks/load_entry_by_title/", dict(
      notebook_id = self.notebook.object_id,
      entry_title = "unknown title",
    ), session_id = self.session_id )

    entry = result[ "entry" ]
    assert entry == None

  def test_save_entry( self, startup = False ):
    self.login()

    # save over an existing entry supplying new contents and a new title
    new_entry_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.entry.object_id,
      contents = new_entry_contents,
      startup = startup,
    ), session_id = self.session_id )

    assert result[ "saved" ] == True

    # make sure the old title can no longer be loaded
    result = self.http_post( "/notebooks/load_entry_by_title/", dict(
      notebook_id = self.notebook.object_id,
      entry_title = "my title",
    ), session_id = self.session_id )

    entry = result[ "entry" ]
    assert entry == None

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_entry_by_title/", dict(
      notebook_id = self.notebook.object_id,
      entry_title = "new title",
    ), session_id = self.session_id )

    entry = result[ "entry" ]

    assert entry.object_id == self.entry.object_id
    assert entry.title == self.entry.title
    assert entry.contents == self.entry.contents

    # check that the entry is / is not a startup entry
    if startup:
      assert entry in self.notebook.startup_entries
    else:
      assert not entry in self.notebook.startup_entries

  def test_save_startup_entry( self ):
    self.test_save_entry( startup = True )

  def test_save_entry_without_login( self, startup = False ):
    # save over an existing entry supplying new contents and a new title
    new_entry_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.entry.object_id,
      contents = new_entry_contents,
      startup = startup,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_save_startup_entry_without_login( self ):
    self.test_save_entry_without_login( startup = True )

  def test_save_entry_with_unknown_notebook( self ):
    self.login()

    # save over an existing entry supplying new contents and a new title
    new_entry_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_entry/", dict(
      notebook_id = self.unknown_notebook_id,
      entry_id = self.entry.object_id,
      contents = new_entry_contents,
      startup = False,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_save_new_entry( self, startup = False ):
    self.login()

    # save a completely new entry
    new_entry = Entry( "55", u"<h3>newest title</h3>foo" )
    result = self.http_post( "/notebooks/save_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = new_entry.object_id,
      contents = new_entry.contents,
      startup = startup,
    ), session_id = self.session_id )

    assert result[ "saved" ] == True

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_entry_by_title/", dict(
      notebook_id = self.notebook.object_id,
      entry_title = new_entry.title,
    ), session_id = self.session_id )

    entry = result[ "entry" ]

    assert entry.object_id == new_entry.object_id
    assert entry.title == new_entry.title
    assert entry.contents == new_entry.contents

    # check that the entry is / is not a startup entry
    if startup:
      assert entry in self.notebook.startup_entries
    else:
      assert not entry in self.notebook.startup_entries

  def test_save_new_startup_entry( self ):
    self.test_save_new_entry( startup = True )

  def test_save_new_entry_with_disallowed_tags( self ):
    self.login()

    # save a completely new entry
    title_with_tags = u"<h3>my title</h3>"
    junk = u"foo<script>haxx0r</script>"
    more_junk = u"<p style=\"evil\">blah</p>"
    new_entry = Entry( "55", title_with_tags + junk + more_junk )

    result = self.http_post( "/notebooks/save_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = new_entry.object_id,
      contents = new_entry.contents,
      startup = False,
    ), session_id = self.session_id )

    assert result[ "saved" ] == True

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_entry_by_title/", dict(
      notebook_id = self.notebook.object_id,
      entry_title = new_entry.title,
    ), session_id = self.session_id )

    entry = result[ "entry" ]

    expected_contents = title_with_tags + cgi.escape( junk ) + u"<p>blah</p>"

    assert entry.object_id == new_entry.object_id
    assert entry.title == new_entry.title
    assert entry.contents == expected_contents

  def test_save_new_entry_with_bad_characters( self ):
    self.login()

    # save a completely new entry
    contents = "<h3>newest title</h3>foo"
    junk = "\xa0bar"
    new_entry = Entry( "55", contents + junk )
    result = self.http_post( "/notebooks/save_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = new_entry.object_id,
      contents = new_entry.contents,
      startup = False,
    ), session_id = self.session_id )

    assert result[ "saved" ] == True

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_entry_by_title/", dict(
      notebook_id = self.notebook.object_id,
      entry_title = new_entry.title,
    ), session_id = self.session_id )

    entry = result[ "entry" ]

    assert entry.object_id == new_entry.object_id
    assert entry.title == new_entry.title
    assert entry.contents == contents + " bar"

  def test_add_startup_entry( self ):
    self.login()

    result = self.http_post( "/notebooks/add_startup_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.entry2.object_id,
    ), session_id = self.session_id )

    # test that the added entry shows up in notebook.startup_entries
    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert len( notebook.startup_entries ) == 2
    assert notebook.startup_entries[ 0 ] == self.entry
    assert notebook.startup_entries[ 1 ] == self.entry2

  def test_add_startup_entry_without_login( self ):
    result = self.http_post( "/notebooks/add_startup_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.entry2.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_add_startup_entry_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/add_startup_entry/", dict(
      notebook_id = self.unknown_notebook_id,
      entry_id = self.entry2.object_id,
    ), session_id = self.session_id )

    # test that notebook.startup_entries hasn't changed
    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert len( notebook.startup_entries ) == 1
    assert notebook.startup_entries[ 0 ] == self.entry

  def test_add_startup_unknown_entry( self ):
    self.login()

    result = self.http_post( "/notebooks/add_startup_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.unknown_entry_id,
    ), session_id = self.session_id )

    # test that notebook.startup_entries hasn't changed
    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert len( notebook.startup_entries ) == 1
    assert notebook.startup_entries[ 0 ] == self.entry

  def test_remove_startup_entry( self ):
    self.login()

    result = self.http_post( "/notebooks/remove_startup_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.entry.object_id,
    ), session_id = self.session_id )

    # test that the remove entry no longer shows up in notebook.startup_entries
    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert len( notebook.startup_entries ) == 0

  def test_remove_startup_entry_without_login( self ):
    result = self.http_post( "/notebooks/remove_startup_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.entry.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_remove_startup_entry_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/remove_startup_entry/", dict(
      notebook_id = self.unknown_notebook_id,
      entry_id = self.entry.object_id,
    ), session_id = self.session_id )

    # test that notebook.startup_entries hasn't changed
    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert len( notebook.startup_entries ) == 1
    assert notebook.startup_entries[ 0 ] == self.entry

  def test_remove_startup_unknown_entry( self ):
    self.login()

    result = self.http_post( "/notebooks/remove_startup_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.unknown_entry_id,
    ), session_id = self.session_id )

    # test that notebook.startup_entries hasn't changed
    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert len( notebook.startup_entries ) == 1
    assert notebook.startup_entries[ 0 ] == self.entry

  def test_delete_entry( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.entry.object_id,
    ), session_id = self.session_id )

    # test that the delete entry is actually deleted
    result = self.http_post( "/notebooks/load_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.entry.object_id,
    ), session_id = self.session_id )

    assert result.get( "entry" ) == None

  def test_delete_entry_without_login( self ):
    result = self.http_post( "/notebooks/delete_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.entry.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_delete_entry_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_entry/", dict(
      notebook_id = self.unknown_notebook_id,
      entry_id = self.entry.object_id,
    ), session_id = self.session_id )

    # test that the entry hasn't been deleted
    result = self.http_post( "/notebooks/load_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.entry.object_id,
    ), session_id = self.session_id )

    entry = result.get( "entry" )
    assert entry.object_id == self.entry.object_id

  def test_delete_unknown_entry( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.unknown_entry_id,
    ), session_id = self.session_id )

    # test that the entry hasn't been deleted
    result = self.http_post( "/notebooks/load_entry/", dict(
      notebook_id = self.notebook.object_id,
      entry_id = self.entry.object_id,
    ), session_id = self.session_id )

    entry = result.get( "entry" )
    assert entry.object_id == self.entry.object_id

  def test_blank_entry( self ):
    result = self.http_get( "/notebooks/blank_entry/5" )
    assert result[ u"id" ] == u"5"

  def test_search( self ):
    self.login()

    search_text = u"bla"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    entries = result.get( "entries" )

    assert len( entries ) == 1
    assert entries[ 0 ].object_id == self.entry.object_id

  def test_search_without_login( self ):
    search_text = u"bla"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_case_insensitive_search( self ):
    self.login()

    search_text = u"bLA"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    entries = result.get( "entries" )

    assert len( entries ) == 1
    assert entries[ 0 ].object_id == self.entry.object_id

  def test_empty_search( self ):
    self.login()

    search_text = ""

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    entries = result.get( "entries" )

    assert len( entries ) == 0

  def test_search_with_no_results( self ):
    self.login()

    search_text = "doesn't match anything"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    entries = result.get( "entries" )

    assert len( entries ) == 0

  def test_search_title_and_contents( self ):
    self.login()

    # ensure that entries with titles matching the search text show up before entries with only
    # contents matching the search text
    entry3 = Entry( "55", u"<h3>blah</h3>foo" )
    self.notebook.add_entry( entry3 )

    self.database.save( self.notebook )

    search_text = "bla"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    entries = result.get( "entries" )

    assert len( entries ) == 2
    assert entries[ 0 ].object_id == entry3.object_id
    assert entries[ 1 ].object_id == self.entry.object_id

  def test_search_html_tags( self ):
    self.login()

    search_text = "h3"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    entries = result.get( "entries" )

    assert len( entries ) == 0

  def test_recent_entries( self ):
    self.login()

    result = self.http_post( "/notebooks/recent_entries/", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    entries = result.get( "entries" )

    assert len( entries ) == 2
    assert entries[ 0 ].object_id == self.entry2.object_id
    assert entries[ 1 ].object_id == self.entry.object_id

  def test_recent_entries_without_login( self ):
    result = self.http_post( "/notebooks/recent_entries/", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_download_html( self ):
    self.login()

    entry3 = Entry( "55", u"<h3>blah</h3>foo" )
    self.notebook.add_entry( entry3 )

    result = self.http_get(
      "/notebooks/download_html/%s" % self.notebook.object_id,
      session_id = self.session_id,
    )
    assert result.get( "notebook_name" ) == self.notebook.name

    entries = result.get( "entries" )
    assert len( entries ) == len( self.notebook.entries )
    startup_entry_allowed = True
    previous_revision = None

    # assert that startup entries come first, then normal entries in descending revision order
    for entry in entries:
      if entry in self.notebook.startup_entries:
        assert startup_entry_allowed
      else:
        startup_entry_allowed = False
        assert entry in self.notebook.entries
        if previous_revision:
          assert entry.revision < previous_revision

        previous_revision = entry.revision
      
  def test_download_html( self ):
    entry3 = Entry( "55", u"<h3>blah</h3>foo" )
    self.notebook.add_entry( entry3 )

    result = self.http_get(
      "/notebooks/download_html/%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    assert result.get( "error" )
      
  def test_download_html_with_unknown_notebook( self ):
    self.login()

    result = self.http_get(
      "/notebooks/download_html/%s" % self.unknown_notebook_id,
      session_id = self.session_id,
    )

    assert result.get( "error" )

  def login( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username,
      password = self.password,
      login_button = u"login",
    ) )
    self.session_id = result[ u"session_id" ]
