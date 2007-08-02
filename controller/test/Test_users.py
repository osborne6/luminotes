import cherrypy
from Test_controller import Test_controller
from controller.Scheduler import Scheduler
from model.User import User
from model.Notebook import Notebook


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

  def test_current_after_signup( self ):
    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      signup_button = u"sign up",
    ) )
    session_id = result[ u"session_id" ]

    new_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]

    result = self.http_get( "/users/current", session_id = session_id )

    assert result[ u"user" ].username == self.new_username
    notebooks = result[ u"notebooks" ]
    assert len( notebooks ) == 2
    assert notebooks[ 0 ] == self.anon_notebook
    notebook = notebooks[ 1 ]
    assert notebook.object_id == new_notebook_id
    assert len( notebook.notes ) == 1
    assert len( notebook.startup_notes ) == 1

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

    assert result[ u"redirect" ] == u"/"
    assert result[ u"deauthenticated" ]

  def test_current_after_login( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username,
      password = self.password,
      login_button = u"login",
    ) )
    session_id = result[ u"session_id" ]

    result = self.http_get( "/users/current", session_id = session_id )

    assert result[ u"user" ] == self.user
    assert result[ u"notebooks" ] == [ self.anon_notebook ] + self.notebooks
    assert result[ u"http_url" ] == self.settings[ u"global" ].get( u"luminotes.http_url" )

  def test_current_without_login( self ):
    result = self.http_get( "/users/current" )

    assert result[ u"user" ].username == "anonymous"
    assert result[ u"notebooks" ] == [ self.anon_notebook ]
    assert result[ u"http_url" ] == self.settings[ u"global" ].get( u"luminotes.http_url" )
