import cherrypy
import cgi
from urllib import quote
from Test_controller import Test_controller
from controller.Scheduler import Scheduler
from model.Notebook import Notebook
from model.Note import Note
from model.User import User


class Test_notebooks( Test_controller ):
  def setUp( self ):
    Test_controller.setUp( self )

    self.notebook = None
    self.anon_notebook = None
    self.unknown_notebook_id = "17"
    self.unknown_note_id = "42"
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
    self.trash = Notebook( ( yield Scheduler.SLEEP ), u"trash", )
    self.database.next_id( self.scheduler.thread )
    self.notebook = Notebook( ( yield Scheduler.SLEEP ), u"notebook", self.trash )

    self.database.next_id( self.scheduler.thread )
    note_id = ( yield Scheduler.SLEEP )
    self.note = Note( note_id, u"<h3>my title</h3>blah" )
    self.note_duplicate = Note( note_id, u"<h3>my title</h3>blah" )
    self.notebook.add_note( self.note )
    self.notebook.add_startup_note( self.note )

    self.database.next_id( self.scheduler.thread )
    self.note2 = Note( ( yield Scheduler.SLEEP ), u"<h3>other title</h3>whee" )
    self.notebook.add_note( self.note2 )
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

  def test_default_with_note( self ):
    result = self.http_get( "/notebooks/%s?note_id=%s" % ( self.notebook.object_id, self.note.object_id ) )
    
    assert result.get( u"notebook_id" ) == self.notebook.object_id
    assert result.get( u"note_id" ) == self.note.object_id

  def test_default_with_note_and_revision( self ):
    result = self.http_get( "/notebooks/%s?note_id=%s&revision=%s" % (
      self.notebook.object_id,
      self.note.object_id,
      quote( unicode( self.note.revision ) ),
    ) )
    
    assert result.get( u"notebook_id" ) == self.notebook.object_id
    assert result.get( u"note_id" ) == self.note.object_id
    assert result.get( u"revision" ) == unicode( self.note.revision )

  def test_contents( self ):
    self.login()

    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert notebook.object_id == self.notebook.object_id
    assert len( notebook.startup_notes ) == 1
    assert notebook.startup_notes[ 0 ] == self.note

  def test_contents_with_note( self ):
    self.login()

    result = self.http_get(
      "/notebooks/contents?notebook_id=%s&note_id=%s" % ( self.notebook.object_id, self.note.object_id ),
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert notebook.object_id == self.notebook.object_id
    assert len( notebook.startup_notes ) == 1
    assert notebook.startup_notes[ 0 ] == self.note

    note = result[ "note" ]

    assert note.object_id == self.note.object_id

  def test_contents_with_note_and_revision( self ):
    self.login()

    result = self.http_get(
      "/notebooks/contents?notebook_id=%s&note_id=%s&revision=%s" % (
        self.notebook.object_id,
        self.note.object_id,
        quote( unicode( self.note.revision ) ),
      ),
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert notebook.object_id == self.notebook.object_id
    assert len( notebook.startup_notes ) == 1
    assert notebook.startup_notes[ 0 ] == self.note

    note = result[ "note" ]

    assert note.object_id == self.note.object_id

  def test_contents_without_login( self ):
    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    assert result.get( "error" )

  def test_load_note( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == self.note.title
    assert note.contents == self.note.contents

  def test_load_note_with_revision( self ):
    self.login()

    # update the note to generate a new revision
    previous_revision = self.note.revision
    previous_title = self.note.title
    previous_contents = self.note.contents
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
    ), session_id = self.session_id )

    # load the note by the old revision
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      revision = previous_revision,
    ), session_id = self.session_id )

    note = result[ "note" ]

    # assert that we get the previous revision of the note, not the new one
    assert note.object_id == self.note.object_id
    assert note.revision == previous_revision
    assert note.title == previous_title
    assert note.contents == previous_contents

  def test_load_note_without_login( self ):
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_load_note_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.unknown_notebook_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_load_unknown_note( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.unknown_note_id,
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None

  def test_load_note_by_title( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == self.note.title
    assert note.contents == self.note.contents

  def test_load_note_by_title_without_login( self ):
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_load_note_by_title_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.unknown_notebook_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_load_unknown_note_by_title( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "unknown title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None

  def test_lookup_note_id( self ):
    self.login()

    result = self.http_post( "/notebooks/lookup_note_id/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "note_id" ) == self.note.object_id

  def test_lookup_note_id_without_login( self ):
    result = self.http_post( "/notebooks/lookup_note_id/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_lookup_note_id_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/lookup_note_id/", dict(
      notebook_id = self.unknown_notebook_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_lookup_unknown_note_id( self ):
    self.login()

    result = self.http_post( "/notebooks/lookup_note_id/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "unknown title",
    ), session_id = self.session_id )

    assert result.get( "note_id" ) == None

  def test_save_note( self, startup = False ):
    self.login()

    # save over an existing note supplying new contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
    ), session_id = self.session_id )

    assert result[ "new_revision" ] and result[ "new_revision" ] != previous_revision

    # make sure the old title can no longer be loaded
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "my title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == self.note.title
    assert note.contents == self.note.contents

    # check that the note is / is not a startup note
    if startup:
      assert note in self.notebook.startup_notes
    else:
      assert not note in self.notebook.startup_notes

  def test_save_startup_note( self ):
    self.test_save_note( startup = True )

  def test_save_note_without_login( self, startup = False ):
    # save over an existing note supplying new contents and a new title
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_save_startup_note_without_login( self ):
    self.test_save_note_without_login( startup = True )

  def test_save_note_with_unknown_notebook( self ):
    self.login()

    # save over an existing note supplying new contents and a new title
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.unknown_notebook_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = False,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_save_new_note( self, startup = False ):
    self.login()

    # save a completely new note
    new_note = Note( "55", u"<h3>newest title</h3>foo" )
    previous_revision = new_note.revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = new_note.object_id,
      contents = new_note.contents,
      startup = startup,
    ), session_id = self.session_id )

    assert result[ "new_revision" ] and result[ "new_revision" ] != previous_revision

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = new_note.title,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == new_note.object_id
    assert note.title == new_note.title
    assert note.contents == new_note.contents

    # check that the note is / is not a startup note
    if startup:
      assert note in self.notebook.startup_notes
    else:
      assert not note in self.notebook.startup_notes

  def test_save_new_startup_note( self ):
    self.test_save_new_note( startup = True )

  def test_save_new_note_with_disallowed_tags( self ):
    self.login()

    # save a completely new note
    title_with_tags = u"<h3>my title</h3>"
    junk = u"foo<script>haxx0r</script>"
    more_junk = u"<p style=\"evil\">blah</p>"
    new_note = Note( "55", title_with_tags + junk + more_junk )
    previous_revision = new_note.revision

    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = new_note.object_id,
      contents = new_note.contents,
      startup = False,
    ), session_id = self.session_id )

    assert result[ "new_revision" ] and result[ "new_revision" ] != previous_revision

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = new_note.title,
    ), session_id = self.session_id )

    note = result[ "note" ]

    expected_contents = title_with_tags + cgi.escape( junk ) + u"<p>blah</p>"

    assert note.object_id == new_note.object_id
    assert note.title == new_note.title
    assert note.contents == expected_contents

  def test_save_new_note_with_bad_characters( self ):
    self.login()

    # save a completely new note
    contents = "<h3>newest title</h3>foo"
    junk = "\xa0bar"
    new_note = Note( "55", contents + junk )
    previous_revision = new_note.revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = new_note.object_id,
      contents = new_note.contents,
      startup = False,
    ), session_id = self.session_id )

    assert result[ "new_revision" ] and result[ "new_revision" ] != previous_revision

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = new_note.title,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == new_note.object_id
    assert note.title == new_note.title
    assert note.contents == contents + " bar"

  def test_add_startup_note( self ):
    self.login()

    result = self.http_post( "/notebooks/add_startup_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note2.object_id,
    ), session_id = self.session_id )

    # test that the added note shows up in notebook.startup_notes
    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert len( notebook.startup_notes ) == 2
    assert notebook.startup_notes[ 0 ] == self.note
    assert notebook.startup_notes[ 1 ] == self.note2

  def test_add_startup_note_without_login( self ):
    result = self.http_post( "/notebooks/add_startup_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note2.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_add_startup_note_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/add_startup_note/", dict(
      notebook_id = self.unknown_notebook_id,
      note_id = self.note2.object_id,
    ), session_id = self.session_id )

    # test that notebook.startup_notes hasn't changed
    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert len( notebook.startup_notes ) == 1
    assert notebook.startup_notes[ 0 ] == self.note

  def test_add_startup_unknown_note( self ):
    self.login()

    result = self.http_post( "/notebooks/add_startup_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.unknown_note_id,
    ), session_id = self.session_id )

    # test that notebook.startup_notes hasn't changed
    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert len( notebook.startup_notes ) == 1
    assert notebook.startup_notes[ 0 ] == self.note

  def test_remove_startup_note( self ):
    self.login()

    result = self.http_post( "/notebooks/remove_startup_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    # test that the remove note no longer shows up in notebook.startup_notes
    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert len( notebook.startup_notes ) == 0

  def test_remove_startup_note_without_login( self ):
    result = self.http_post( "/notebooks/remove_startup_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_remove_startup_note_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/remove_startup_note/", dict(
      notebook_id = self.unknown_notebook_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    # test that notebook.startup_notes hasn't changed
    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert len( notebook.startup_notes ) == 1
    assert notebook.startup_notes[ 0 ] == self.note

  def test_remove_startup_unknown_note( self ):
    self.login()

    result = self.http_post( "/notebooks/remove_startup_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.unknown_note_id,
    ), session_id = self.session_id )

    # test that notebook.startup_notes hasn't changed
    result = self.http_get(
      "/notebooks/contents?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    notebook = result[ "notebook" ]

    assert len( notebook.startup_notes ) == 1
    assert notebook.startup_notes[ 0 ] == self.note

  def test_is_startup_note( self ):
    self.login()

    assert self.notebook.is_startup_note( self.note ) == True
    assert self.notebook.is_startup_note( self.note2 ) == False

    # make sure that a different note object with the same id as self.note is considered a startup note
    assert self.notebook.is_startup_note( self.note_duplicate ) == True

  def test_delete_note( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    # test that the deleted note is actually deleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "note" ) == None

    # test that the note get moved to the trash
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from == self.notebook.object_id

  def test_delete_note_without_login( self ):
    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_delete_note_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.unknown_notebook_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    # test that the note hasn't been deleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note.object_id == self.note.object_id

  def test_delete_unknown_note( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.unknown_note_id,
    ), session_id = self.session_id )

    # test that the note hasn't been deleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note.object_id == self.note.object_id

  def test_undelete_note( self ):
    self.login()

    # first delete the note
    self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.unknown_note_id,
    ), session_id = self.session_id )

    # then undelete it
    self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    # test that the undeleted note is actually undeleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from == None

    # test that the note is no longer in the trash
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "note" ) == None

  def test_undelete_note_without_login( self ):
    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_undelete_note_with_unknown_notebook( self ):
    self.login()

    self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.unknown_notebook_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

    # test that the note hasn't been undeleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note.object_id == self.note.object_id
    assert note.deleted_from == self.notebook.object_id

  def test_undelete_unknown_note( self ):
    self.login()

    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.unknown_note_id,
    ), session_id = self.session_id )

    # test that the note hasn't been deleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note.object_id == self.note.object_id
    assert note.deleted_from == None

  def test_undelete_note_from_incorrect_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.anon_notebook,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

    # test that the note hasn't been undeleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note.object_id == self.note.object_id
    assert note.deleted_from == self.notebook.object_id

  def test_blank_note( self ):
    result = self.http_get( "/notebooks/blank_note/5" )
    assert result[ u"id" ] == u"5"

  def test_search_titles_without_titles_only( self ):
    self.login()

    search_text = u"other"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
      titles_only = False,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note2.object_id

  def test_search_contents_without_titles_only( self ):
    self.login()

    search_text = u"bla"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
      titles_only = False,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note.object_id

  def test_search_titles_with_titles_only( self ):
    self.login()

    search_text = u"other"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
      titles_only = True,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note2.object_id

  def test_search_contents_with_titles_only( self ):
    self.login()

    search_text = u"bla"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
      titles_only = True,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 0

  def test_search_without_login( self ):
    search_text = u"bla"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
      titles_only = True,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_case_insensitive_search( self ):
    self.login()

    search_text = u"bLA"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
      titles_only = False,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note.object_id

  def test_empty_search( self ):
    self.login()

    search_text = ""

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
      titles_only = True,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 0

  def test_search_with_no_results( self ):
    self.login()

    search_text = "doesn't match anything"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
      titles_only = True,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 0

  def test_search_title_and_contents( self ):
    self.login()

    # ensure that notes with titles matching the search text show up before notes with only
    # contents matching the search text
    note3 = Note( "55", u"<h3>blah</h3>foo" )
    self.notebook.add_note( note3 )

    self.database.save( self.notebook )

    search_text = "bla"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
      titles_only = False,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 2
    assert notes[ 0 ].object_id == note3.object_id
    assert notes[ 1 ].object_id == self.note.object_id

  def test_search_html_tags( self ):
    self.login()

    search_text = "h3"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
      titles_only = True,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 0

  def test_search_character_refs( self ):
    self.login()

    note3 = Note( "55", u"<h3>foo: bar</h3>baz" )
    self.notebook.add_note( note3 )

    search_text = "oo: b"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
      titles_only = True,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == note3.object_id

  def test_recent_notes( self ):
    self.login()

    result = self.http_post( "/notebooks/recent_notes/", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 2
    assert notes[ 0 ].object_id == self.note2.object_id
    assert notes[ 1 ].object_id == self.note.object_id

  def test_recent_notes_without_login( self ):
    result = self.http_post( "/notebooks/recent_notes/", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_download_html( self ):
    self.login()

    note3 = Note( "55", u"<h3>blah</h3>foo" )
    self.notebook.add_note( note3 )

    result = self.http_get(
      "/notebooks/download_html/%s" % self.notebook.object_id,
      session_id = self.session_id,
    )
    assert result.get( "notebook_name" ) == self.notebook.name

    notes = result.get( "notes" )
    assert len( notes ) == len( self.notebook.notes )
    startup_note_allowed = True
    previous_revision = None

    # assert that startup notes come first, then normal notes in descending revision order
    for note in notes:
      if self.notebook.is_startup_note( note ):
        assert startup_note_allowed
      else:
        startup_note_allowed = False
        assert note in self.notebook.notes
        if previous_revision:
          assert note.revision < previous_revision

        previous_revision = note.revision
      
  def test_download_html( self ):
    note3 = Note( "55", u"<h3>blah</h3>foo" )
    self.notebook.add_note( note3 )

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
