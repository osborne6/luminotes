import cherrypy
from model.Note import Note
from model.Notebook import Notebook
from model.User import User
from controller.Scheduler import Scheduler
from Test_controller import Test_controller


class Test_root( Test_controller ):
  def setUp( self ):
    Test_controller.setUp( self )

    self.notebook = Notebook.create( self.database.next_id( Notebook ), u"my notebook" )
    self.database.save( self.notebook )

    self.anon_notebook = Notebook.create( self.database.next_id( Notebook ), u"anon notebook" )
    self.database.save( self.anon_notebook )
    self.anon_note = Note.create(
      self.database.next_id( Note ), u"<h3>my note</h3>",
      notebook_id = self.anon_notebook.object_id,
    )
    self.database.save( self.anon_note )

    self.username = u"mulder"
    self.password = u"trustno1"
    self.email_address = u"outthere@example.com"
    self.user = None
    self.session_id = None

    self.user = User.create( self.database.next_id( User ), self.username, self.password, self.email_address )
    self.database.save( self.user )
    self.database.execute( self.user.sql_save_notebook( self.notebook.object_id ) )

    self.anonymous = User.create( self.database.next_id( User ), u"anonymous" )
    self.database.save( self.anonymous )
    self.database.execute( self.anonymous.sql_save_notebook( self.anon_notebook.object_id ) )

  def test_index( self ):
    result = self.http_get( "/" )
    assert result

  def test_index_after_login( self ):
    self.login()

    result = self.http_get(
      "/",
      session_id = self.session_id,
    )

    assert result.get( u"redirect" )
    assert result.get( u"redirect" ).startswith( self.settings[ u"global" ][ u"luminotes.https_url" ] )

  def test_index_with_https_after_login( self ):
    self.login()

    result = self.http_get(
      "/",
      session_id = self.session_id,
      pretend_https = True,
    )

    assert result
    assert result.get( u"redirect" ) is None

  def test_default( self ):
    result = self.http_get(
      "/my_note",
    )

    assert result
    assert result[ u"note" ]
    assert result[ u"note" ].object_id == self.anon_note.object_id

  def test_default_with_unknown_note( self ):
    result = self.http_get(
      "/unknown_note",
    )

    body = result.get( u"body" )
    assert body
    assert len( body ) > 0
    assert u"404" in body[ 0 ]

  def test_default_with_login_note( self ):
    result = self.http_get(
      "/login",
    )

    assert result
    assert result.get( "redirect" )
    assert result.get( "redirect" ).startswith( "https://" )

  def test_default_with_sign_up_note( self ):
    result = self.http_get(
      "/sign_up",
    )

    assert result
    assert result.get( "redirect" )
    assert result.get( "redirect" ).startswith( "https://" )

  def test_next_id( self ):
    result = self.http_get( "/next_id" )

    assert result.get( "next_id" )

    result = self.http_get( "/next_id" )

    assert result.get( "next_id" )

  def test_404( self ):
    result = self.http_get( "/four_oh_four" )

    body = result.get( u"body" )
    assert body
    assert len( body ) > 0
    assert u"404" in body[ 0 ]

    status = result.get( u"status" )
    assert u"404" in status

    headers = result.get( u"headers" )
    status = headers.get( u"status" )
    assert u"404" in status

  def login( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username,
      password = self.password,
      login_button = u"login",
    ) )
    self.session_id = result[ u"session_id" ]

  def test_redeem_reset( self ):
    redeem_reset_id = u"foobarbaz"
    result = self.http_get( "/r/%s" % redeem_reset_id )

    assert result[ u"redirect" ] == u"/users/redeem_reset/%s" % redeem_reset_id
