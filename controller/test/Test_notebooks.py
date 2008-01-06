import cherrypy
import cgi
from nose.tools import raises
from urllib import quote
from Test_controller import Test_controller
from model.Notebook import Notebook
from model.Note import Note
from model.User import User
from model.Invite import Invite
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
    self.username2 = u"deepthroat"
    self.password2 = u"mmmtobacco"
    self.email_address2 = u"parkinglot@example.com"
    self.user = None
    self.user2 = None
    self.invite = None
    self.anonymous = None
    self.session_id = None

    self.make_users()
    self.make_notebooks()
    self.make_invites()
    self.database.commit()

  def make_notebooks( self ):
    user_id = self.user.object_id

    self.trash = Notebook.create( self.database.next_id( Notebook ), u"trash", user_id = user_id )
    self.database.save( self.trash, commit = False )
    self.notebook = Notebook.create( self.database.next_id( Notebook ), u"notebook", self.trash.object_id, user_id = user_id )
    self.database.save( self.notebook, commit = False )

    note_id = self.database.next_id( Note )
    self.note = Note.create( note_id, u"<h3>my title</h3>blah", notebook_id = self.notebook.object_id, startup = True, user_id = user_id )
    self.database.save( self.note, commit = False )

    note_id = self.database.next_id( Note )
    self.note2 = Note.create( note_id, u"<h3>other title</h3>whee", notebook_id = self.notebook.object_id, user_id = user_id )
    self.database.save( self.note2, commit = False )

    self.anon_notebook = Notebook.create( self.database.next_id( Notebook ), u"anon_notebook", user_id = user_id )
    self.database.save( self.anon_notebook, commit = False )

    self.database.execute( self.user.sql_save_notebook( self.notebook.object_id, read_write = True, owner = True ) )
    self.database.execute( self.user.sql_save_notebook( self.notebook.trash_id, read_write = True, owner = True ) )
    self.database.execute( self.user.sql_save_notebook( self.anon_notebook.object_id, read_write = False, owner = False ) )

    self.database.execute( self.user2.sql_save_notebook( self.notebook.object_id, read_write = True, owner = False ) )
    self.database.execute( self.user2.sql_save_notebook( self.notebook.trash_id, read_write = True, owner = False ) )

  def make_users( self ):
    self.user = User.create( self.database.next_id( User ), self.username, self.password, self.email_address )
    self.database.save( self.user, commit = False )

    self.user2 = User.create( self.database.next_id( User ), self.username2, self.password2, self.email_address2 )
    self.database.save( self.user2, commit = False )

    self.anonymous = User.create( self.database.next_id( User ), u"anonymous" )
    self.database.save( self.anonymous, commit = False )

  def make_invites( self ):
    self.invite = Invite.create(
      self.database.next_id( Invite ), self.user.object_id, self.notebook.object_id,
      u"skinner@example.com", read_write = True, owner = False,
    )
    self.database.save( self.invite, commit = False )

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
    assert result.get( u"notebooks" )[ 0 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 0 ].read_write == True
    assert result.get( u"notebooks" )[ 0 ].owner == True
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == True
    assert result.get( u"notebook" ).owner == True
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_as_preview_viewer( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?preview=viewer" % self.notebook.object_id,
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 1
    assert result.get( u"notebooks" )[ 0 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 0 ].read_write == False
    assert result.get( u"notebooks" )[ 0 ].owner == False
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == False
    assert result.get( u"notebook" ).owner == False
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_as_preview_collaborator( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?preview=collaborator" % self.notebook.object_id,
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 1
    assert result.get( u"notebooks" )[ 0 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 0 ].read_write == True
    assert result.get( u"notebooks" )[ 0 ].owner == False
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == True
    assert result.get( u"notebook" ).owner == False
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_as_preview_owner( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?preview=owner" % self.notebook.object_id,
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 0 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 0 ].read_write == True
    assert result.get( u"notebooks" )[ 0 ].owner == True
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == True
    assert result.get( u"notebook" ).owner == True
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_as_preview_viewer_with_viewer_access( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?preview=viewer" % self.anon_notebook.object_id,
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 1
    assert result.get( u"notebooks" )[ 0 ].object_id == self.anon_notebook.object_id
    assert result.get( u"notebooks" )[ 0 ].read_write == False
    assert result.get( u"notebooks" )[ 0 ].owner == False
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.anon_notebook.object_id
    assert result.get( u"notebook" ).read_write == False
    assert result.get( u"notebook" ).owner == False
    assert len( result.get( u"startup_notes" ) ) == 0
    assert result[ "total_notes_count" ] == 0
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert len( result[ "invites" ] ) == 0

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_as_preview_collaborator_with_viewer_access( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?preview=collaborator" % self.anon_notebook.object_id,
      session_id = self.session_id,
    )
    
    # even though a collaborator preview is being requested, this user only has preview-level
    # access. so read_write should be False on the returned notebook
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 1
    assert result.get( u"notebooks" )[ 0 ].object_id == self.anon_notebook.object_id
    assert result.get( u"notebooks" )[ 0 ].read_write == False
    assert result.get( u"notebooks" )[ 0 ].owner == False
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.anon_notebook.object_id
    assert result.get( u"notebook" ).read_write == False
    assert result.get( u"notebook" ).owner == False
    assert len( result.get( u"startup_notes" ) ) == 0
    assert result[ "total_notes_count" ] == 0
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert len( result[ "invites" ] ) == 0

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_as_preview_owner_with_viewer_access( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?preview=owner" % self.anon_notebook.object_id,
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 2 ].object_id == self.anon_notebook.object_id
    assert result.get( u"notebooks" )[ 2 ].read_write == False
    assert result.get( u"notebooks" )[ 2 ].owner == False
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.anon_notebook.object_id
    assert result.get( u"notebook" ).read_write == False
    assert result.get( u"notebook" ).owner == False
    assert len( result.get( u"startup_notes" ) ) == 0
    assert result[ "total_notes_count" ] == 0
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert len( result[ "invites" ] ) == 0

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
    assert result.get( u"notebooks" )[ 0 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 0 ].read_write == True
    assert result.get( u"notebooks" )[ 0 ].owner == True
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == True
    assert result.get( u"notebook" ).owner == True
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2

    assert result.get( "notes" )
    assert len( result.get( "notes" ) ) == 1
    assert result.get( u"notes" )[ 0 ].object_id == self.note.object_id
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

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
    assert result.get( u"notebooks" )[ 0 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 0 ].read_write == True
    assert result.get( u"notebooks" )[ 0 ].owner == True
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == True
    assert result.get( u"notebook" ).owner == True
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2

    assert result.get( "notes" )
    assert len( result.get( "notes" ) ) == 1
    assert result.get( u"notes" )[ 0 ].object_id == self.note.object_id
    assert result.get( u"notes" )[ 0 ].revision == self.note.revision
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) == False

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

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
    assert result.get( u"notebooks" )[ 0 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 0 ].read_write == True
    assert result.get( u"notebooks" )[ 0 ].owner == True
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == True
    assert result.get( u"notebook" ).owner == True
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == parent_id
    assert result.get( u"note_read_write" ) in ( None, True )

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "total_notes_count" ] == 2
    assert result[ "notes" ] == []

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert notebook.owner == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents_with_read_write_false( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      read_write = False,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "total_notes_count" ] == 2
    assert result[ "notes" ] == []

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == False
    assert notebook.owner == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents_with_owner_false( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      owner = False,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "total_notes_count" ] == 2
    assert result[ "notes" ] == []

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert notebook.owner == False
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
    assert result[ "total_notes_count" ] == 2

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert notebook.owner == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id

    notes = result[ "notes" ]

    assert notes
    assert len( notes ) == 1
    note = notes[ 0 ]
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
    assert result[ "total_notes_count" ] == 2

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert notebook.owner == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id

    notes = result[ "notes" ]

    assert notes
    assert len( notes ) == 1
    note = notes[ 0 ]
    assert note.object_id == self.note.object_id
    assert note.revision == self.note.revision
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents_with_different_invites( self ):
    # create an invite with a different email address from the previous
    invite = Invite.create(
      self.database.next_id( Invite ), self.user.object_id, self.notebook.object_id,
      u"smoking@example.com", read_write = True, owner = False,
    )
    self.database.save( invite )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "total_notes_count" ] == 2
    assert result[ "notes" ] == []

    invites = result[ "invites" ]
    assert len( invites ) == 2
    invite = invites[ 0 ]
    assert invite.object_id == invite.object_id
    invite = invites[ 1 ]
    assert invite.object_id == self.invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert notebook.owner == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents_with_duplicate_invites( self ):
    # create an invite with the same email address as the previous invite
    invite = Invite.create(
      self.database.next_id( Invite ), self.user.object_id, self.notebook.object_id,
      u"skinner@example.com", read_write = True, owner = False,
    )
    self.database.save( invite )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "total_notes_count" ] == 2
    assert result[ "notes" ] == []

    # the two invites should be collapsed down into one
    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert notebook.owner == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id
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
    assert result[ "notes" ] == []
    assert result[ "total_notes_count" ] == 0
    assert result[ "invites" ] == []

    assert notebook.object_id == self.anon_notebook.object_id
    assert notebook.read_write == False
    assert notebook.owner == False
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

  def test_load_note_with_incorrect_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.anon_notebook.object_id,
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

  def test_load_note_with_summary( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      summarize = True,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == self.note.title
    assert note.contents == self.note.contents
    assert note.summary == u"blah"
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

  def test_load_note_by_title_with_summary( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title,
      summarize = True,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == self.note.title
    assert note.contents == self.note.contents
    assert note.summary == u"blah"
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_summarize_note( self ):
    note = cherrypy.root.notebooks.summarize_note( self.note )

    assert note.summary == u"blah"

  def test_summarize_note_truncated_at_word_boundary( self ):
    self.note.contents = u"<h3>the title</h3>" + u"foo bar baz quux " * 10
    note = cherrypy.root.notebooks.summarize_note( self.note )

    assert note.summary == u"foo bar baz quux foo bar baz quux foo ..."

  def test_summarize_note_truncated_at_character_boundary( self ):
    self.note.contents = u"<h3>the title</h3>" + u"foobarbazquux" * 10
    note = cherrypy.root.notebooks.summarize_note( self.note )

    assert note.summary == u"foobarbazquuxfoobarbazquuxfoobarbazquuxf ..."

  def test_summarize_note_with_short_words( self ):
    self.note.contents = u"<h3>the title</h3>" + u"a b c d e f g h i j k l"
    note = cherrypy.root.notebooks.summarize_note( self.note )

    assert note.summary == u"a b c d e f g h i j ..."

  def test_summarize_note_without_title( self ):
    self.note.contents = "foo bar baz quux"
    note = cherrypy.root.notebooks.summarize_note( self.note )

    assert note.summary == u"foo bar baz quux"

  def test_summarize_note_without_contents( self ):
    self.note.contents = None
    note = cherrypy.root.notebooks.summarize_note( self.note )

    assert note.summary == None

  def test_summarize_note_none( self ):
    note = cherrypy.root.notebooks.summarize_note( None )

    assert note == None

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
    assert revisions[ 0 ].revision == self.note.revision
    assert revisions[ 0 ].user_id == self.user.object_id
    assert revisions[ 0 ].username == self.username

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

    assert result[ "new_revision" ]
    assert result[ "new_revision" ].revision != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    current_revision = result[ "new_revision" ].revision
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
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
    assert note.user_id == self.user.object_id

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
    assert revisions[ 0 ].revision == previous_revision
    assert revisions[ 0 ].user_id == self.user.object_id
    assert revisions[ 0 ].username == self.username
    assert revisions[ 1 ].revision == current_revision
    assert revisions[ 1 ].user_id == self.user.object_id
    assert revisions[ 1 ].username == self.username

  def test_save_startup_note( self ):
    self.test_save_note( startup = True )

  def test_save_note_by_different_user( self, startup = False ):
    self.login2()

    # save over an existing note as a different user, supplying new contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    assert result[ "new_revision" ]
    assert result[ "new_revision" ].revision != previous_revision
    assert result[ "new_revision" ].user_id == self.user2.object_id
    assert result[ "new_revision" ].username == self.username2
    current_revision = result[ "new_revision" ].revision
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username

    self.login()

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
    assert note.user_id == self.user2.object_id

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
    assert revisions[ 0 ].revision == previous_revision
    assert revisions[ 0 ].user_id == self.user.object_id
    assert revisions[ 0 ].username == self.username
    assert revisions[ 1 ].revision == current_revision
    assert revisions[ 1 ].user_id == self.user2.object_id
    assert revisions[ 1 ].username == self.username2

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

    assert result[ "new_revision" ]
    assert result[ "new_revision" ].revision != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
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
    assert note.user_id == self.user.object_id

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
    previous_revision = result[ "new_revision" ].revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # assert that the note wasn't actually updated the second time
    assert result[ "new_revision" ] == None
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
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
    assert note.user_id == self.user.object_id
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
    previous_revision = result[ "new_revision" ].revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # assert that the note wasn't actually updated the second time
    assert result[ "new_revision" ] == None
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
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
    assert note.user_id == self.user.object_id
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
    previous_revision = result[ "new_revision" ].revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = not startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # assert that the note was updated the second time
    assert result[ "new_revision" ]
    assert result[ "new_revision" ].revision != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
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
    assert note.user_id == self.user.object_id
    assert note.revision > previous_revision
    assert note.startup == ( not startup )

    if note.startup:
      assert note.rank == 0 
    else:
      assert note.rank is None

  def test_save_unchanged_note_with_extra_newline( self, startup = False ):
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

    # now attempt to save over that note again without changing the contents,
    # except for adding a newline
    user = self.database.load( User, self.user.object_id )
    previous_storage_bytes = user.storage_bytes
    previous_revision = result[ "new_revision" ].revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents + u"\n",
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # assert that the note wasn't actually updated the second time
    assert result[ "new_revision" ] == None
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
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
    assert note.user_id == self.user.object_id
    assert note.revision == previous_revision

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
    second_revision = result[ "new_revision" ].revision
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
    assert result[ "new_revision" ].revision not in ( first_revision, second_revision )
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    assert result[ "previous_revision" ].revision == second_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
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
    assert note.user_id == self.user.object_id

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

    assert result[ "new_revision" ]
    assert result[ "new_revision" ] != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
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
    assert note.user_id == self.user.object_id

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

    assert result[ "new_revision" ]
    assert result[ "new_revision" ] != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
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
    assert note.user_id == self.user.object_id

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

    assert result[ "new_revision" ]
    assert result[ "new_revision" ] != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
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
    assert note.user_id == self.user.object_id

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

    assert result[ "new_revision" ]
    assert result[ "new_revision" ] != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
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
    assert note.user_id == self.user.object_id

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
    assert result[ "note_id_in_trash" ] == self.note.object_id

    # test that the deleted note can be loaded from the trash
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note
    assert note.object_id == self.note.object_id
    assert note.title == self.note.title
    assert note.contents == self.note.contents
    assert note.startup == self.note.startup
    assert note.deleted_from_id == self.notebook.object_id
    assert note.user_id == self.user.object_id

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

    # get the revision of the deleted note
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.trash.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )
    deleted_revision = result[ "note" ].revision

    # then undelete the note
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
    assert note.user_id == self.user.object_id

    # test that the revision of the note from when it was deleted is loadable
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      revision = deleted_revision,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == self.notebook.object_id
    assert note.notebook_id == self.trash.object_id
    assert note.user_id == self.user.object_id

  def test_undelete_note_that_is_not_deleted( self ):
    self.login()

    # "undelete" the note
    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" ) == None

    # test that the "undeleted" note is where it should be
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
    assert note.user_id == self.user.object_id

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
    assert note.user_id == self.user.object_id

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
    assert note.user_id == self.user.object_id

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
    assert note.user_id == self.user.object_id

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

    # test that all notes can be loaded from the trash
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == self.notebook.object_id
    assert note.notebook_id == self.notebook.trash_id
    assert note.user_id == self.user.object_id

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash_id,
      note_id = self.note2.object_id,
    ), session_id = self.session_id )

    note2 = result.get( "note" )
    assert note2
    assert note2.object_id == self.note2.object_id
    assert note2.deleted_from_id == self.notebook.object_id
    assert note2.notebook_id == self.notebook.trash_id
    assert note2.user_id == self.user.object_id

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

    assert result[ "error" ]
    assert u"missing" in result[ "error" ]

  def test_long_search( self ):
    self.login()

    search_text = "w" * 257

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert result[ "error" ]
    assert u"too long" in result[ "error" ]

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

  def test_create( self ):
    self.login()

    result = self.http_post( "/notebooks/create", dict(), session_id = self.session_id )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

    new_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ].split( u"?" )[ 0 ]
    notebook = self.database.last_saved_obj

    assert isinstance( notebook, Notebook )
    assert notebook.object_id == new_notebook_id
    assert notebook.name == u"new notebook"
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.trash_id

  def test_contents_after_create( self ):
    self.login()

    result = self.http_post( "/notebooks/create", dict(), session_id = self.session_id )
    new_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ].split( u"?" )[ 0 ]

    result = cherrypy.root.notebooks.contents(
      notebook_id = new_notebook_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    assert result[ "total_notes_count" ] == 0
    assert result[ "startup_notes" ] == []
    assert result[ "notes" ] == []
    assert result[ "invites" ] == []

    assert notebook.object_id == new_notebook_id
    assert notebook.read_write == True
    assert notebook.owner == True

  def test_create_without_login( self ):
    result = self.http_post( "/notebooks/create", dict() )

    assert result[ u"error" ]

  def test_rename( self ):
    self.login()

    new_name = u"renamed notebook"
    result = self.http_post( "/notebooks/rename", dict(
      notebook_id = self.notebook.object_id,
      name = new_name,
    ), session_id = self.session_id )

    assert u"error" not in result

  def test_contents_after_rename( self ):
    self.login()

    new_name = u"renamed notebook"
    self.http_post( "/notebooks/rename", dict(
      notebook_id = self.notebook.object_id,
      name = new_name,
    ), session_id = self.session_id )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    assert notebook.name == new_name
    assert notebook.user_id == self.user.object_id

  def test_rename_without_login( self ):
    new_name = u"renamed notebook"
    result = self.http_post( "/notebooks/rename", dict(
      notebook_id = self.notebook.object_id,
      name = new_name,
    ) )

    assert result[ u"error" ]

  def test_rename_trash( self ):
    self.login()

    new_name = u"renamed notebook"
    result = self.http_post( "/notebooks/rename", dict(
      notebook_id = self.notebook.trash_id,
      name = new_name,
    ), session_id = self.session_id )

    assert u"error" in result

  def test_rename_with_reserved_luminotes_name( self ):
    self.login()

    new_name = u"Luminotes blog"
    result = self.http_post( "/notebooks/rename", dict(
      notebook_id = self.notebook.object_id,
      name = new_name,
    ), session_id = self.session_id )

    assert result[ u"error" ]

  def test_rename_with_reserved_trash_name( self ):
    self.login()

    new_name = u" trash  "
    result = self.http_post( "/notebooks/rename", dict(
      notebook_id = self.notebook.object_id,
      name = new_name,
    ), session_id = self.session_id )

    assert result[ u"error" ]

  def test_delete( self ):
    self.login()

    result = self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

    # assert that we're redirected to a newly created notebook
    remaining_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ].split( u"?" )[ 0 ]
    notebook = self.database.last_saved_obj

    assert isinstance( notebook, Notebook )
    assert notebook.object_id == remaining_notebook_id
    assert notebook.name == u"my notebook"
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.trash_id
    assert notebook.user_id == self.user.object_id

  def test_delete_with_multiple_notebooks( self ):
    # create a second notebook, which we should be redirected to after the first notebook is deleted
    trash = Notebook.create( self.database.next_id( Notebook ), u"trash" )
    self.database.save( trash, commit = False )
    notebook = Notebook.create( self.database.next_id( Notebook ), u"notebook", trash.object_id )
    self.database.save( notebook, commit = False )
    self.database.execute( self.user.sql_save_notebook( notebook.object_id, read_write = True, owner = True ) )
    self.database.execute( self.user.sql_save_notebook( notebook.trash_id, read_write = True, owner = True ) )
    self.database.commit()

    self.login()

    result = self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

    # assert that we're redirected to the second notebook
    remaining_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ].split( u"?" )[ 0 ]
    assert remaining_notebook_id
    assert remaining_notebook_id == notebook.object_id

  def test_contents_after_delete( self ):
    self.login()

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    assert notebook.deleted == True
    assert notebook.user_id == self.user.object_id

  def test_contents_after_delete_twice( self ):
    self.login()

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    assert notebook.deleted == True
    assert notebook.user_id == self.user.object_id

  def test_delete_without_login( self ):
    result = self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"error" ]

  def test_delete_trash( self ):
    self.login()

    result = self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.trash_id,
    ), session_id = self.session_id )

    assert u"error" in result

  def test_delete_forever( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_forever", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert u"error" not in result

  @raises( Access_error )
  def test_contents_after_delete_forever( self ):
    self.login()

    self.http_post( "/notebooks/delete_forever", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

  def test_delete_then_delete_forever( self ):
    self.login()

    result = self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/delete_forever", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert u"error" not in result

  @raises( Access_error )
  def test_contents_after_delete_then_delete_forever( self ):
    self.login()

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    self.http_post( "/notebooks/delete_forever", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

  def test_delete_forever_without_login( self ):
    result = self.http_post( "/notebooks/delete_forever", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"error" ]

  def test_delete_forever_trash( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_forever", dict(
      notebook_id = self.notebook.trash_id,
    ), session_id = self.session_id )

    assert u"error" in result

  def test_undelete( self ):
    self.login()

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/undelete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

    # assert that we're redirected to the undeleted notebook
    notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]
    notebook = self.database.last_saved_obj

    assert isinstance( notebook, Notebook )
    assert notebook.object_id == notebook_id
    assert notebook.name == self.notebook.name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.trash_id
    assert notebook.user_id == self.user.object_id

  def test_contents_after_undelete( self ):
    self.login()

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/undelete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    assert notebook.deleted == False
    assert notebook.user_id == self.user.object_id

  def test_undelete_without_login( self ):
    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/undelete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"error" ]

  def test_undelete_twice( self ):
    self.login()

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    self.http_post( "/notebooks/undelete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/undelete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

    # assert that we're redirected to the undeleted notebook
    notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]
    notebook = self.database.last_saved_obj

    assert isinstance( notebook, Notebook )
    assert notebook.object_id == notebook_id
    assert notebook.name == self.notebook.name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.trash_id
    assert notebook.user_id == self.user.object_id

  def test_recent_notes( self ):
    result = cherrypy.root.notebooks.load_recent_notes(
      self.notebook.object_id,
      user_id = self.user.object_id,
    )

    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2

    notes = result.get( u"notes" )
    assert notes
    assert len( notes ) == 2
    assert notes[ 0 ].object_id == self.note2.object_id
    assert notes[ 1 ].object_id == self.note.object_id

    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert result.get( u"start" ) == 0
    assert result.get( u"count" ) == 10

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_recent_notes_with_start( self ):
    result = cherrypy.root.notebooks.load_recent_notes(
      self.notebook.object_id,
      start = 1,
      user_id = self.user.object_id,
    )

    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2

    notes = result.get( u"notes" )
    assert notes
    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note.object_id

    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert result.get( u"start" ) == 1
    assert result.get( u"count" ) == 10

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_recent_notes_with_count( self ):
    result = cherrypy.root.notebooks.load_recent_notes(
      self.notebook.object_id,
      count = 1,
      user_id = self.user.object_id,
    )

    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2

    notes = result.get( u"notes" )
    assert notes
    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note2.object_id

    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert result.get( u"start" ) == 0
    assert result.get( u"count" ) == 1

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  @raises( Access_error )
  def test_recent_notes_with_unknown_notebok( self ):
    result = cherrypy.root.notebooks.load_recent_notes(
      self.unknown_notebook_id,
      user_id = self.user.object_id,
    )

  @raises( Access_error )
  def test_recent_notes_with_incorrect_user( self ):
    result = cherrypy.root.notebooks.load_recent_notes(
      self.notebook.object_id,
      user_id = self.anonymous.object_id,
    )

  def login( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username,
      password = self.password,
      login_button = u"login",
    ) )
    self.session_id = result[ u"session_id" ]

  def login2( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username2,
      password = self.password2,
      login_button = u"login",
    ) )
    self.session_id = result[ u"session_id" ]
