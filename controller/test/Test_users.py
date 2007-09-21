import cherrypy
from Test_controller import Test_controller
from controller.Scheduler import Scheduler
from model.User import User
from model.Notebook import Notebook
from model.Note import Note


class Test_users( Test_controller ):
  def setUp( self ):
    Test_controller.setUp( self )

    self.username = u"mulder"
    self.password = u"trustno1"
    self.email_address = u"outthere@example.com"
    self.new_username = u"reynolds"
    self.new_password = u"shiny"
    self.new_email_address = u"capn@example.com"
    self.user = None
    self.anonymous = None
    self.notebooks = None

    thread = self.make_users()
    self.scheduler.add( thread )
    self.scheduler.wait_for( thread )

  def make_users( self ):
    self.database.next_id( self.scheduler.thread )
    notebook_id1 = ( yield Scheduler.SLEEP )
    self.database.next_id( self.scheduler.thread )
    notebook_id2 = ( yield Scheduler.SLEEP )

    self.notebooks = [
      Notebook( notebook_id1, u"my notebook" ),
      Notebook( notebook_id2, u"my other notebook" ),
    ]

    self.database.next_id( self.scheduler.thread )
    self.anon_notebook = Notebook( ( yield Scheduler.SLEEP ), u"anon notebook" )
    self.database.next_id( self.scheduler.thread )
    self.startup_note = Note( ( yield Scheduler.SLEEP ), u"<h3>login</h3>" )
    self.anon_notebook.add_note( self.startup_note )
    self.anon_notebook.add_startup_note( self.startup_note )

    self.database.next_id( self.scheduler.thread )
    self.user = User( ( yield Scheduler.SLEEP ), self.username, self.password, self.email_address, self.notebooks )
    self.database.next_id( self.scheduler.thread )
    self.anonymous = User( ( yield Scheduler.SLEEP ), u"anonymous", None, None, [ self.anon_notebook ] )

    self.database.save( self.user )
    self.database.save( self.anonymous )

  def test_signup( self ):
    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      signup_button = u"sign up",
    ) )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )
    assert result[ u"authenticated" ]

  def test_current_after_signup( self, include_startup_notes = False ):
    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      signup_button = u"sign up",
    ) )
    session_id = result[ u"session_id" ]

    new_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]

    result = self.http_get(
      "/users/current?include_startup_notes=%s" % include_startup_notes,
      session_id = session_id,
    )

    assert result[ u"user" ].username == self.new_username
    notebooks = result[ u"notebooks" ]
    assert len( notebooks ) == 2
    assert notebooks[ 0 ] == self.anon_notebook
    assert notebooks[ 0 ].trash == None

    notebook = notebooks[ 1 ]
    assert notebook.object_id == new_notebook_id
    assert notebook.trash
    assert len( notebook.notes ) == 1
    assert len( notebook.startup_notes ) == 1

    startup_notes = result[ "startup_notes" ]
    if include_startup_notes:
      assert len( startup_notes ) == 1
      assert startup_notes[ 0 ] == self.startup_note
    else:
      assert startup_notes == []

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337

  def test_current_with_startup_notes_after_signup( self ):
    self.test_current_after_signup( include_startup_notes = True )

  def test_signup_with_different_passwords( self ):
    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password + u"nomatch",
      email_address = self.new_email_address,
      signup_button = u"sign up",
    ) )

    assert result[ u"error" ]

  def test_login( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username,
      password = self.password,
      login_button = u"login",
    ) )

    assert result[ u"redirect" ] == u"/notebooks/%s" % self.notebooks[ 0 ].object_id
    assert result[ u"authenticated" ]

  def test_login_with_unknown_user( self ):
    result = self.http_post( "/users/login", dict(
      username = u"nosuchuser",
      password = self.password,
      login_button = u"login",
    ) )

    assert result[ u"error" ]
    assert not result.get( u"authenticated" )

  def test_login_with_invalid_password( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username,
      password = u"wrongpass",
      login_button = u"login",
    ) )

    assert result[ u"error" ]
    assert not result.get( u"authenticated" )

  def test_logout( self ):
    result = self.http_post( "/users/logout", dict() )

    assert result[ u"redirect" ] == self.settings[ u"global" ].get( u"luminotes.http_url" ) + u"/"
    assert result[ u"deauthenticated" ]

  def test_current_after_login( self, include_startup_notes = False ):
    result = self.http_post( "/users/login", dict(
      username = self.username,
      password = self.password,
      login_button = u"login",
    ) )
    session_id = result[ u"session_id" ]

    result = self.http_get(
      "/users/current?include_startup_notes=%s" % include_startup_notes,
      session_id = session_id,
    )

    assert result[ u"user" ] == self.user
    assert result[ u"notebooks" ] == [ self.anon_notebook ] + self.notebooks
    assert result[ u"http_url" ] == self.settings[ u"global" ].get( u"luminotes.http_url" )
    assert result[ u"login_url" ] == None

    startup_notes = result[ "startup_notes" ]
    if include_startup_notes:
      assert len( startup_notes ) == 1
      assert startup_notes[ 0 ] == self.startup_note
    else:
      assert startup_notes == []

  def test_current_with_startup_notes_after_login( self ):
    self.test_current_after_login( include_startup_notes = True )

  def test_current_without_login( self, include_startup_notes = False ):
    result = self.http_get(
      "/users/current?include_startup_notes=%s" % include_startup_notes,
    )

    assert result[ u"user" ].username == "anonymous"
    assert result[ u"notebooks" ] == [ self.anon_notebook ]
    assert result[ u"http_url" ] == self.settings[ u"global" ].get( u"luminotes.http_url" )

    login_note = self.anon_notebook.lookup_note_by_title( u"login" )
    assert result[ u"login_url" ] == u"%s/notebooks/%s?note_id=%s" % (
      self.settings[ u"global" ][ u"luminotes.https_url" ],
      self.anon_notebook.object_id,
      login_note.object_id,
    )

    startup_notes = result[ "startup_notes" ]
    if include_startup_notes:
      assert len( startup_notes ) == 1
      assert startup_notes[ 0 ] == self.startup_note
    else:
      assert startup_notes == []

  def test_current_with_startup_notes_without_login( self ):
    self.test_current_without_login( include_startup_notes = True )

  def test_calculate_user_storage( self ):
    size = cherrypy.root.users.calculate_storage( self.user )
    notebooks = self.user.notebooks

    # expected a sum of the sizes of all of this user's notebooks, notes, and revisions
    expected_size = \
      self.database.size( notebooks[ 0 ].object_id ) + \
      self.database.size( notebooks[ 1 ].object_id )

    assert size == expected_size

  def test_calculate_anon_storage( self ):
    size = cherrypy.root.users.calculate_storage( self.anonymous )

    expected_size = \
      self.database.size( self.anon_notebook.object_id ) + \
      self.database.size( self.anon_notebook.notes[ 0 ].object_id ) + \
      self.database.size( self.anon_notebook.notes[ 0 ].object_id, self.anon_notebook.notes[ 0 ].revision )

    assert size == expected_size

  def test_update_storage( self ):
    previous_revision = self.user.revision

    cherrypy.root.users.update_storage( self.user.object_id )
    self.scheduler.wait_until_idle()

    expected_size = cherrypy.root.users.calculate_storage( self.user )

    assert self.user.storage_bytes == expected_size
    assert self.user.revision > previous_revision

  def test_update_storage_with_unknown_user_id( self ):
    original_revision = self.user.revision

    cherrypy.root.users.update_storage( 77 )
    self.scheduler.wait_until_idle()

    expected_size = cherrypy.root.users.calculate_storage( self.user )

    assert self.user.storage_bytes == 0
    assert self.user.revision == original_revision

  def test_update_storage_with_callback( self ):
    def gen():
      previous_revision = self.user.revision

      cherrypy.root.users.update_storage( self.user.object_id, self.scheduler.thread )
      user = ( yield Scheduler.SLEEP )

      expected_size = cherrypy.root.users.calculate_storage( self.user )
      assert user == self.user
      assert self.user.storage_bytes == expected_size
      assert self.user.revision > previous_revision

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )
