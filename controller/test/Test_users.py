import re
import cherrypy
import smtplib
from datetime import datetime, timedelta
from nose.tools import raises
from Test_controller import Test_controller
from Stub_smtp import Stub_smtp
from controller.Scheduler import Scheduler
from model.User import User
from model.Notebook import Notebook
from model.Note import Note
from model.User_list import User_list


class Test_users( Test_controller ):
  RESET_LINK_PATTERN = re.compile( "(https?://\S+)?/(\S+)" )

  def setUp( self ):
    Test_controller.setUp( self )

    self.username = u"mulder"
    self.password = u"trustno1"
    self.email_address = u"outthere@example.com"
    self.new_username = u"reynolds"
    self.new_password = u"shiny"
    self.new_email_address = u"capn@example.com"
    self.username2 = u"scully"
    self.password2 = u"trustsome1"
    self.email_address2 = u"outthere@example.com"
    self.user = None
    self.user2 = None
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
    self.user2 = User( ( yield Scheduler.SLEEP ), self.username2, self.password2, self.email_address2 )
    self.database.next_id( self.scheduler.thread )
    self.anonymous = User( ( yield Scheduler.SLEEP ), u"anonymous", None, None, [ self.anon_notebook ] )

    self.database.next_id( self.scheduler.thread )
    user_list_id = ( yield Scheduler.SLEEP )
    user_list = User_list( user_list_id, u"all" )
    user_list.add_user( self.user )
    user_list.add_user( self.user2 )
    user_list.add_user( self.anonymous )

    self.database.save( self.user )
    self.database.save( self.user2 )
    self.database.save( self.anonymous )
    self.database.save( user_list )

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

  def test_send_reset( self ):
    # trick send_reset() into using a fake SMTP server
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    result = self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )
    session_id = result[ u"session_id" ]
    
    assert u"has been sent to" in result[ u"message" ]
    assert smtplib.SMTP.connected == False
    assert "<%s>" % self.settings[ u"global" ][ u"luminotes.support_email" ] in smtplib.SMTP.from_address
    assert smtplib.SMTP.to_addresses == [ self.user.email_address ]
    assert u"password reset" in smtplib.SMTP.message
    assert self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )

  def test_send_reset_to_unknown_email_address( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    result = self.http_post( "/users/send_reset", dict(
      email_address = u"unknown@example.com",
      send_reset_button = u"email me",
    ) )
    
    assert u"no Luminotes user" in result[ u"error" ]
    assert smtplib.SMTP.connected == False
    assert smtplib.SMTP.from_address == None
    assert smtplib.SMTP.to_addresses == None
    assert smtplib.SMTP.message == None

  def test_redeem_reset( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert result[ u"notebook_id" ] == self.anonymous.notebooks[ 0 ].object_id
    assert result[ u"note_id" ]
    assert u"password reset" in result[ u"note_contents" ]
    assert self.user.username in result[ u"note_contents" ]
    assert self.user2.username in result[ u"note_contents" ]

  def test_redeem_reset_unknown( self ):
    password_reset_id = u"unknownresetid"
    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert u"expired" in result[ u"error" ]

  def test_redeem_reset_expired( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    # to trigger expiration, pretend that the password reset was made 25 hours ago
    def gen():
      self.database.load( password_reset_id, self.scheduler.thread )
      password_reset = ( yield Scheduler.SLEEP )
      password_reset._Persistent__revision = datetime.now() - timedelta( hours = 25 )
      self.database.save( password_reset )

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert u"expired" in result[ u"error" ]

  def test_redeem_reset_already_redeemed( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    def gen():
      self.database.load( password_reset_id, self.scheduler.thread )
      password_reset = ( yield Scheduler.SLEEP )
      password_reset.redeemed = True
      self.database.save( password_reset )

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert u"already" in result[ u"error" ]

  def test_redeem_reset_unknown_email( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    def gen():
      self.database.load( password_reset_id, self.scheduler.thread )
      password_reset = ( yield Scheduler.SLEEP )
      password_reset._Password_reset__email_address = u"unknown@example.com"
      self.database.save( password_reset )

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert u"email address" in result[ u"error" ]

  def test_reset_password( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    new_password = u"newpass"
    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, new_password ),
      ( self.user.object_id, new_password ),
      ( self.user2.object_id, u"" ),
      ( self.user2.object_id, u"" ),
    ) )

    # check that the password reset is now marked as redeemed
    def gen():
      self.database.load( password_reset_id, self.scheduler.thread )
      password_reset = ( yield Scheduler.SLEEP )
      assert password_reset.redeemed

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

    # check that the password was actually reset for one of the users, but not the other
    assert self.user.check_password( new_password )
    assert self.user2.check_password( self.password2 )
    assert result[ u"redirect" ]

  def test_reset_password_unknown_reset_id( self ):
    new_password = u"newpass"
    password_reset_id = u"unknownresetid"
    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, new_password ),
      ( self.user.object_id, new_password ),
      ( self.user2.object_id, u"" ),
      ( self.user2.object_id, u"" ),
    ) )

    # check that neither user's password has changed
    assert self.user.check_password( self.password )
    assert self.user2.check_password( self.password2 )
    assert u"expired" in result[ "error" ]

  def test_reset_password_invalid_reset_id( self ):
    new_password = u"newpass"
    password_reset_id = u"invalid reset id"
    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, new_password ),
      ( self.user.object_id, new_password ),
      ( self.user2.object_id, u"" ),
      ( self.user2.object_id, u"" ),
    ) )

    # check that neither user's password has changed
    assert self.user.check_password( self.password )
    assert self.user2.check_password( self.password2 )
    assert u"valid" in result[ "error" ]

  def test_reset_password_expired( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    # to trigger expiration, pretend that the password reset was made 25 hours ago
    def gen():
      self.database.load( password_reset_id, self.scheduler.thread )
      password_reset = ( yield Scheduler.SLEEP )
      password_reset._Persistent__revision = datetime.now() - timedelta( hours = 25 )
      self.database.save( password_reset )

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

    new_password = u"newpass"
    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, new_password ),
      ( self.user.object_id, new_password ),
      ( self.user2.object_id, u"" ),
      ( self.user2.object_id, u"" ),
    ) )

    # check that the password reset is not marked as redeemed
    def gen():
      self.database.load( password_reset_id, self.scheduler.thread )
      password_reset = ( yield Scheduler.SLEEP )
      assert password_reset.redeemed == False

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

    # check that neither user's password has changed
    assert self.user.check_password( self.password )
    assert self.user2.check_password( self.password2 )
    assert u"expired" in result[ "error" ]

  def test_reset_password_expired( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    def gen():
      self.database.load( password_reset_id, self.scheduler.thread )
      password_reset = ( yield Scheduler.SLEEP )
      password_reset.redeemed = True

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

    new_password = u"newpass"
    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, new_password ),
      ( self.user.object_id, new_password ),
      ( self.user2.object_id, u"" ),
      ( self.user2.object_id, u"" ),
    ) )

    # check that neither user's password has changed
    assert self.user.check_password( self.password )
    assert self.user2.check_password( self.password2 )
    assert u"already" in result[ "error" ]

  def test_reset_password_unknown_user_id( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    new_password = u"newpass"
    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, new_password ),
      ( self.user.object_id, new_password ),
      ( u"unknown", u"foo" ),
      ( u"unknown", u"foo" ),
      ( self.user2.object_id, u"" ),
      ( self.user2.object_id, u"" ),
    ) )

    # check that neither user's password has changed
    assert self.user.check_password( self.password )
    assert self.user2.check_password( self.password2 )
    assert result[ "error" ]

  def test_reset_password_non_matching( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    new_password = u"newpass"
    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, new_password ),
      ( self.user.object_id, u"nonmatchingpass" ),
      ( self.user2.object_id, u"" ),
      ( self.user2.object_id, u"" ),
    ) )

    # check that neither user's password has changed
    assert self.user.check_password( self.password )
    assert self.user2.check_password( self.password2 )
    assert result[ "error" ]

  def test_reset_password_blank( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, u"" ),
      ( self.user.object_id, u"" ),
      ( self.user2.object_id, u"" ),
      ( self.user2.object_id, u"" ),
    ) )

    # check that neither user's password has changed
    assert self.user.check_password( self.password )
    assert self.user2.check_password( self.password2 )
    assert result[ "error" ]

  def test_reset_password_multiple_users( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    new_password = u"newpass"
    new_password2 = u"newpass2"
    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, new_password ),
      ( self.user.object_id, new_password ),
      ( self.user2.object_id, new_password2 ),
      ( self.user2.object_id, new_password2 ),
    ) )

    # check that the password reset is now marked as redeemed
    def gen():
      self.database.load( password_reset_id, self.scheduler.thread )
      password_reset = ( yield Scheduler.SLEEP )
      assert password_reset.redeemed

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

    # check that the password was actually reset for both users
    assert self.user.check_password( new_password )
    assert self.user2.check_password( new_password2 )
    assert result[ u"redirect" ]
