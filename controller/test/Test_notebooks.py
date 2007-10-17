import cherrypy
import cgi
from nose.tools import raises
from urllib import quote
from Test_controller import Test_controller
from model.Notebook import Notebook
from model.Note import Note
from model.User import User
from controller.Notebooks import Access_error


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

    self.make_notebooks()
    self.make_users()
    self.database.commit()

  def make_notebooks( self ):
    self.trash = Notebook.create( self.database.next_id( Notebook ), u"trash" )
    self.database.save( self.trash, commit = False )
    self.notebook = Notebook.create( self.database.next_id( Notebook ), u"notebook", self.trash.object_id )
    self.database.save( self.notebook, commit = False )

    note_id = self.database.next_id( Note )
    self.note = Note.create( note_id, u"<h3>my title</h3>blah", notebook_id = self.notebook.object_id, startup = True )
    self.database.save( self.note, commit = False )

    note_id = self.database.next_id( Note )
    self.note2 = Note.create( note_id, u"<h3>other title</h3>whee", notebook_id = self.notebook.object_id )
    self.database.save( self.note2, commit = False )

    self.anon_notebook = Notebook.create( self.database.next_id( Notebook ), u"anon_notebook" )
    self.database.save( self.anon_notebook, commit = False )

  def make_users( self ):
    self.user = User.create( self.database.next_id( User ), self.username, self.password, self.email_address )
    self.database.save( self.user, commit = False )
    self.database.execute( self.user.sql_save_notebook( self.notebook.object_id, read_write = True ) )
    self.database.execute( self.user.sql_save_notebook( self.notebook.trash_id, read_write = True ) )

    self.anonymous = User.create( self.database.next_id( User ), u"anonymous" )
    self.database.save( self.anonymous, commit = False )
    self.database.execute( self.user.sql_save_notebook( self.anon_notebook.object_id, read_write = False ) )

  def test_default_without_login( self ):
    result = self.http_get(
      "/notebooks/%s" % self.notebook.object_id,
    )
    
    assert u"access" in result[ u"error" ]
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s" % self.notebook.object_id,
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result.get( u"note" ) is None
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_with_note( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?note_id=%s" % ( self.notebook.object_id, self.note.object_id ),
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result.get( u"note" ).object_id == self.note.object_id
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_with_note_and_revision( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?note_id=%s&revision=%s" % (
        self.notebook.object_id,
        self.note.object_id,
        quote( unicode( self.note.revision ) ),
      ),
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result.get( u"note" ).object_id == self.note.object_id
    assert result.get( u"note" ).revision == self.note.revision
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) == False

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_with_parent( self ):
    self.login()

    parent_id = u"foo"
    result = self.http_get(
      "/notebooks/%s?parent_id=%s" % ( self.notebook.object_id, parent_id ),
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result.get( u"note" ) is None
    assert result.get( u"parent_id" ) == parent_id
    assert result.get( u"note_read_write" ) in ( None, True )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "note" ] == None

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents_with_note( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents_with_note_and_revision( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      revision = unicode( self.note.revision ),
      user_id = self.user.object_id,
    )
    self.login()

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.revision == self.note.revision
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  @raises( Access_error )
  def test_contents_without_user_id( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
    )

  @raises( Access_error )
  def test_contents_with_incorrect_user_id( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.anonymous.object_id,
    )

  @raises( Access_error )
  def test_contents_with_unknown_notebook_id( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.unknown_notebook_id,
      user_id = self.user.object_id,
    )

  def test_contents_with_read_only_notebook( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.anon_notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "note" ] == None

    assert notebook.object_id == self.anon_notebook.object_id
    assert notebook.read_write == False
    assert len( startup_notes ) == 0
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

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
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

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
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

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
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_unknown_note( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.unknown_note_id,
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_without_notebook( self ):
    self.login()

    self.note.notebook_id = None
    self.database.save( self.note )

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

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
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_by_title_without_login( self ):
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "error" )
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_by_title_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.unknown_notebook_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "error" )
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_unknown_note_by_title( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "unknown title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_lookup_note_id( self ):
    self.login()

    result = self.http_post( "/notebooks/lookup_note_id/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "note_id" ) == self.note.object_id
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_lookup_note_id_without_login( self ):
    result = self.http_post( "/notebooks/lookup_note_id/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "error" )
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_lookup_note_id_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/lookup_note_id/", dict(
      notebook_id = self.unknown_notebook_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "error" )
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_lookup_unknown_note_id( self ):
    self.login()

    result = self.http_post( "/notebooks/lookup_note_id/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "unknown title",
    ), session_id = self.session_id )

    assert result.get( "note_id" ) == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_revisions( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_revisions/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    revisions = result[ "revisions" ]
    assert revisions != None
    assert len( revisions ) == 1
    assert revisions[ 0 ] == self.note.revision

  def test_save_note( self, startup = False ):
    self.login()

    # save over an existing note, supplying new contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    assert result[ "new_revision" ] and result[ "new_revision" ] != previous_revision
    current_revision = result[ "new_revision" ]
    assert result[ "previous_revision" ] == previous_revision
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

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
    assert note.title == "new title"
    assert note.contents == new_note_contents
    assert note.startup == startup

    if startup:
      assert note.rank == 0 
    else:
      assert note.rank is None

    # make sure that the correct revisions are returned and are in chronological order
    result = self.http_post( "/notebooks/load_note_revisions/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    revisions = result[ "revisions" ]
    assert revisions != None
    assert len( revisions ) == 2
    assert revisions[ 0 ] == previous_revision
    assert revisions[ 1 ] == current_revision

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
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_save_startup_note_without_login( self ):
    self.test_save_note_without_login( startup = True )

  def test_save_deleted_note( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    # save over a deleted note, supplying new contents and a new title. this should cause the note
    # to be automatically undeleted
    deleted_note = self.database.load( Note, self.note.object_id )
    previous_revision = deleted_note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = False,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    assert result[ "new_revision" ] and result[ "new_revision" ] != previous_revision
    assert result[ "previous_revision" ] == previous_revision
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # make sure the old title can no longer be loaded
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "my title",
    ), session_id = self.session_id )

    assert result[ "note" ] == None

    # make sure the new title is now loadable from the notebook
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note
    assert note.object_id == self.note.object_id
    assert note.title == "new title"
    assert note.contents == new_note_contents
    assert note.deleted_from_id == None

    # make sure the old title can no longer be loaded from the trash
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.trash_id,
      note_title = "my title",
    ), session_id = self.session_id )

    assert result[ "note" ] == None

    # make sure the new title is not loadable from the trash either
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.trash_id,
      note_title = "new title",
    ), session_id = self.session_id )

    assert result[ "note" ] == None

  def test_save_unchanged_note( self, startup = False ):
    self.login()

    # save over an existing note, supplying new contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # now attempt to save over that note again without changing the contents
    user = self.database.load( User, self.user.object_id )
    previous_storage_bytes = user.storage_bytes
    previous_revision = result[ "new_revision" ]
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # assert that the note wasn't actually updated the second time
    assert result[ "new_revision" ] == None
    assert result[ "previous_revision" ] == previous_revision
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == previous_storage_bytes
    assert result[ "storage_bytes" ] == 0

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note
    assert note.object_id == self.note.object_id
    assert note.title == "new title"
    assert note.contents == new_note_contents
    assert note.revision == previous_revision

  def test_save_unchanged_deleted_note( self, startup = False ):
    self.login()

    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    # save over an existing deleted note, supplying new contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # now attempt to save over that note again without changing the contents
    user = self.database.load( User, self.user.object_id )
    previous_storage_bytes = user.storage_bytes
    previous_revision = result[ "new_revision" ]
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # assert that the note wasn't actually updated the second time
    assert result[ "new_revision" ] == None
    assert result[ "previous_revision" ] == previous_revision
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == previous_storage_bytes
    assert result[ "storage_bytes" ] == 0

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note
    assert note.object_id == self.note.object_id
    assert note.title == "new title"
    assert note.contents == new_note_contents
    assert note.revision == previous_revision
    assert note.deleted_from_id == None

    # make sure the note is not loadable from the trash
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.trash_id,
      note_title = "new title",
    ), session_id = self.session_id )

    assert result[ "note" ] == None

  def test_save_unchanged_note_with_startup_change( self, startup = False ):
    self.login()

    # save over an existing note supplying new contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # now attempt to save over that note again without changing the contents, but with a change
    # to its startup flag
    previous_revision = result[ "new_revision" ]
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = not startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # assert that the note was updated the second time
    assert result[ "new_revision" ] and result[ "new_revision" ] != previous_revision
    assert result[ "previous_revision" ] == previous_revision
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note
    assert note.object_id == self.note.object_id
    assert note.title == "new title"
    assert note.contents == new_note_contents
    assert note.revision > previous_revision
    assert note.startup == ( not startup )

    if note.startup:
      assert note.rank == 0 
    else:
      assert note.rank is None

  def test_save_note_from_an_older_revision( self ):
    self.login()

    # save over an existing note supplying new contents and a new title
    first_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = False,
      previous_revision = first_revision,
    ), session_id = self.session_id )

    # save over that note again with new contents, providing the original
    # revision as the previous known revision
    second_revision = result[ "new_revision" ]
    new_note_contents = u"<h3>new new title</h3>new new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = False,
      previous_revision = first_revision,
    ), session_id = self.session_id )

    # make sure the second save actually caused an update
    assert result[ "new_revision" ]
    assert result[ "new_revision" ] not in ( first_revision, second_revision )
    assert result[ "previous_revision" ] == second_revision
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # make sure the first title can no longer be loaded
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "my title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None

    # make sure the second title can no longer be loaded
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new new title",
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == "new new title"
    assert note.contents == new_note_contents

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
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_save_new_note( self, startup = False ):
    self.login()

    # save a completely new note
    new_note = Note.create( "55", u"<h3>newest title</h3>foo" )
    previous_revision = new_note.revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = new_note.object_id,
      contents = new_note.contents,
      startup = startup,
      previous_revision = None,
    ), session_id = self.session_id )

    assert result[ "new_revision" ] and result[ "new_revision" ] != previous_revision
    assert result[ "previous_revision" ] == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = new_note.title,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == new_note.object_id
    assert note.title == new_note.title
    assert note.contents == new_note.contents
    assert note.startup == startup

    if startup:
      assert note.rank == 0 
    else:
      assert note.rank is None

  def test_save_new_startup_note( self ):
    self.test_save_new_note( startup = True )

  def test_save_new_note_with_disallowed_tags( self ):
    self.login()

    # save a completely new note
    title_with_tags = u"<h3>my title</h3>"
    junk = u"foo<script>haxx0r</script>"
    more_junk = u"<p style=\"evil\">blah</p>"
    new_note = Note.create( "55", title_with_tags + junk + more_junk )
    previous_revision = new_note.revision

    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = new_note.object_id,
      contents = new_note.contents,
      startup = False,
      previous_revision = None,
    ), session_id = self.session_id )

    assert result[ "new_revision" ] and result[ "new_revision" ] != previous_revision
    assert result[ "previous_revision" ] == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

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
    new_note = Note.create( "55", contents + junk )
    previous_revision = new_note.revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = new_note.object_id,
      contents = new_note.contents,
      startup = False,
      previous_revision = None,
    ), session_id = self.session_id )

    assert result[ "new_revision" ] and result[ "new_revision" ] != previous_revision
    assert result[ "previous_revision" ] == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = new_note.title,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == new_note.object_id
    assert note.title == new_note.title
    assert note.contents == contents + " bar"

  def test_save_two_new_notes( self, startup = False ):
    self.login()

    # save a completely new note
    new_note = Note.create( "55", u"<h3>newest title</h3>foo" )
    previous_revision = new_note.revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = new_note.object_id,
      contents = new_note.contents,
      startup = startup,
      previous_revision = None,
    ), session_id = self.session_id )

    user = self.database.load( User, self.user.object_id )
    previous_storage_bytes = user.storage_bytes

    # save a completely new note
    new_note = Note.create( "56", u"<h3>my title</h3>foo" )
    previous_revision = new_note.revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = new_note.object_id,
      contents = new_note.contents,
      startup = startup,
      previous_revision = None,
    ), session_id = self.session_id )

    assert result[ "new_revision" ] and result[ "new_revision" ] != previous_revision
    assert result[ "previous_revision" ] == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = new_note.title,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == new_note.object_id
    assert note.title == new_note.title
    assert note.contents == new_note.contents
    assert note.startup == startup

    if startup:
      assert note.rank == 1 # one greater than the previous new note's rank 
    else:
      assert note.rank is None

  def test_save_two_new_startup_notes( self ):
    self.test_save_two_new_notes( startup = True )

  def test_delete_note( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # test that the deleted note is actually deleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result[ "note" ] is None

  def test_delete_note_from_trash( self ):
    self.login()

    # first, delete the note from the main notebook, thereby moving it to the trash
    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # then, delete the note from the trash
    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.trash_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # test that the deleted note is actually deleted from the trash
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "note" ) is None

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
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    # then undelete it
    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # test that the undeleted note is actually undeleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == None
    assert note.notebook_id == self.notebook.object_id

  def test_undelete_note_that_is_not_deleted( self ):
    self.login()

    # "undelete" the note
    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" ) == None

    # test that the "undeleted" is where it should be
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == None
    assert note.notebook_id == self.notebook.object_id

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
      notebook_id = self.notebook.trash_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == self.notebook.object_id
    assert note.notebook_id == self.notebook.trash_id

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
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == None
    assert note.notebook_id == self.notebook.object_id

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
      notebook_id = self.notebook.trash_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == self.notebook.object_id
    assert note.notebook_id == self.notebook.trash_id

  def test_undelete_note_that_is_not_deleted_from_id_incorrect_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.anon_notebook,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

    # test that the note is still in its notebook
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == None
    assert note.notebook_id == self.notebook.object_id

  def test_delete_all_notes( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_all_notes/", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # test that all notes are actually deleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result[ "note" ] is None

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note2.object_id,
    ), session_id = self.session_id )

    assert result[ "note" ] is None

  def test_delete_all_notes_from_trash( self ):
    self.login()

    # first, delete all notes from the main notebook, thereby moving them to the trash
    result = self.http_post( "/notebooks/delete_all_notes/", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    # then, delete all notes from the trash
    result = self.http_post( "/notebooks/delete_all_notes/", dict(
      notebook_id = self.notebook.trash_id,
    ), session_id = self.session_id )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # test that all notes are actually deleted from the trash
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "note" ) is None

  def test_delete_all_notes_without_login( self ):
    result = self.http_post( "/notebooks/delete_all_notes/", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_delete_all_notes_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_all_notes/", dict(
      notebook_id = self.unknown_notebook_id,
    ), session_id = self.session_id )

    # test that the notes haven't been deleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note.object_id == self.note.object_id

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note2.object_id,
    ), session_id = self.session_id )

    note2 = result.get( "note" )
    assert note2.object_id == self.note2.object_id

  def test_search_titles( self ):
    self.login()

    search_text = u"other"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note2.object_id

  def test_search_contents( self ):
    self.login()

    search_text = u"bla"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note.object_id

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

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note.object_id

  def test_empty_search( self ):
    self.login()

    search_text = ""

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 0

  def test_search_with_no_results( self ):
    self.login()

    search_text = "doesn't match anything"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 0

  def test_search_title_and_contents( self ):
    self.login()

    # ensure that notes with titles matching the search text show up before notes with only
    # contents matching the search text
    note3 = Note.create( "55", u"<h3>blah</h3>foo", notebook_id = self.notebook.object_id )
    self.database.save( note3 )

    search_text = "bla"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
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
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 0

  def test_search_character_refs( self ):
    self.login()

    note3 = Note.create( "55", u"<h3>foo: bar</h3>baz", notebook_id = self.notebook.object_id )
    self.database.save( note3 )

    search_text = "oo: b"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == note3.object_id

  def test_all_notes( self ):
    self.login()

    result = self.http_post( "/notebooks/all_notes/", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 2
    assert notes[ 0 ][ 0 ] == self.note2.object_id
    assert notes[ 0 ][ 1 ] == self.note2.title
    assert notes[ 1 ][ 0 ] == self.note.object_id
    assert notes[ 1 ][ 1 ] == self.note.title

  def test_all_notes_without_login( self ):
    result = self.http_post( "/notebooks/all_notes/", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_download_html( self ):
    self.login()

    note3 = Note.create( "55", u"<h3>blah</h3>foo", notebook_id = self.notebook.object_id )
    self.database.save( note3 )

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
    note3 = Note.create( "55", u"<h3>blah</h3>foo", notebook_id = self.notebook.object_id )
    self.database.save( note3 )

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
