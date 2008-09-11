import re
import cherrypy
import smtplib
import urllib
from pytz import utc
from nose.tools import raises
from datetime import datetime, timedelta
from Test_controller import Test_controller
import Stub_urllib2
from config.Version import VERSION
from model.User import User
from model.Group import Group
from model.Notebook import Notebook
from model.Note import Note
from model.Password_reset import Password_reset
from model.Download_access import Download_access
from model.Invite import Invite
from controller.Users import Invite_error, Payment_error
import controller.Users as Users


class Test_users( Test_controller ):
  RESET_LINK_PATTERN = re.compile( "(https?://\S+)?/r/(\S+)" )
  INVITE_LINK_PATTERN = re.compile( "(https?://\S+)?/i/(\S+)" )

  def setUp( self ):
    Test_controller.setUp( self )
    Users.urllib2 = Stub_urllib2

    self.username = u"mulder"
    self.password = u"trustno1"
    self.email_address = u"out-there@example.com"
    self.new_username = u"reynolds"
    self.new_password = u"shiny"
    self.new_email_address = u"capn@example.com"
    self.username2 = u"scully"
    self.password2 = u"trustsome1"
    self.email_address2 = u"out-there@example.com"
    self.user = None
    self.user2 = None
    self.group = None
    self.group2 = None
    self.anonymous = None
    self.notebooks = None
    self.session_id = None

    self.make_users()

  def make_users( self ):
    notebook_id1 = self.database.next_id( Notebook )
    notebook_id2 = self.database.next_id( Notebook )
    trash_id1 = self.database.next_id( Notebook )
    trash_id2 = self.database.next_id( Notebook )

    self.database.save( Notebook.create( trash_id1, u"trash" ) )
    self.database.save( Notebook.create( trash_id2, u"trash" ) )

    self.notebooks = [
      Notebook.create( notebook_id1, u"my notebook", trash_id = trash_id1 ),
      Notebook.create( notebook_id2, u"my other notebook", trash_id = trash_id2 ),
    ]
    self.database.save( self.notebooks[ 0 ] )
    self.database.save( self.notebooks[ 1 ] )

    self.anon_notebook = Notebook.create( self.database.next_id( Notebook ), u"anon notebook" )
    self.database.save( self.anon_notebook )
    self.startup_note = Note.create(
      self.database.next_id( Note ), u"<h3>login</h3>",
      notebook_id = self.anon_notebook.object_id, startup = True,
    )
    self.database.save( self.startup_note )

    self.group = Group.create( self.database.next_id( Group ), u"my group" )
    self.database.save( self.group, commit = False )
    self.group2 = Group.create( self.database.next_id( Group ), u"other group" )
    self.database.save( self.group2, commit = False )

    self.user = User.create( self.database.next_id( User ), self.username, self.password, self.email_address )
    self.database.save( self.user, commit = False )
    self.database.execute( self.user.sql_save_notebook( notebook_id1, read_write = True, owner = True, rank = 0 ), commit = False )
    self.database.execute( self.user.sql_save_notebook( trash_id1, read_write = True, owner = True ), commit = False )
    self.database.execute( self.user.sql_save_notebook( notebook_id2, read_write = True, owner = True, rank = 1 ), commit = False )
    self.database.execute( self.user.sql_save_notebook( trash_id2, read_write = True, owner = True ), commit = False )
    self.database.execute( self.user.sql_save_group( self.group.object_id, admin = False ) )

    self.user2 = User.create( self.database.next_id( User ), self.username2, self.password2, self.email_address2, rate_plan = 1 )
    self.database.save( self.user2, commit = False )
    self.database.execute( self.user2.sql_save_group( self.group.object_id, admin = True ) )

    self.anonymous = User.create( self.database.next_id( User ), u"anonymous" )
    self.database.save( self.anonymous, commit = False )
    self.database.execute( self.anonymous.sql_save_notebook( self.anon_notebook.object_id, read_write = False, owner = False ), commit = False )

    self.database.commit()

  def test_signup( self ):
    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      signup_button = u"sign up",
    ) )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

  def test_signup_with_rate_plan( self ):
    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      signup_button = u"sign up",
      rate_plan = u"2",
    ) )

    assert result[ u"redirect" ] == u"/users/subscribe?rate_plan=2&yearly=False"

  def test_signup_with_rate_plan_and_yearly( self ):
    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      signup_button = u"sign up",
      rate_plan = u"2",
      yearly = True,
    ) )

    assert result[ u"redirect" ] == u"/users/subscribe?rate_plan=2&yearly=True"

  def test_signup_without_email_address( self ):
    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = u"",
      signup_button = u"sign up",
    ) )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

  def test_signup_with_invalid_email_address( self ):
    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = u"foo@",
      signup_button = u"sign up",
    ) )

    assert u"error" in result

  def __get_recent_user( self ):
    return self.database.select_one( User, "select * from luminotes_user order by revision desc limit 1;" );

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

    user = self.__get_recent_user()
    assert isinstance( user, User )
    result = cherrypy.root.users.current( user.object_id )

    assert result[ u"user" ].object_id == user.object_id
    assert result[ u"user" ].username == self.new_username
    assert result[ u"user" ].email_address == self.new_email_address

    notebooks = result[ u"notebooks" ]
    notebook = notebooks[ 0 ]
    assert notebook.object_id == notebooks[ 1 ].trash_id
    assert notebook.revision
    assert notebook.name == u"trash"
    assert notebook.trash_id == None
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == None

    notebook = notebooks[ 1 ]
    assert notebook.object_id == new_notebook_id
    assert notebook.revision
    assert notebook.name == u"my notebook"
    assert notebook.trash_id
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    notebook = notebooks[ 2 ]
    assert notebook.object_id == self.anon_notebook.object_id
    assert notebook.revision == self.anon_notebook.revision
    assert notebook.name == self.anon_notebook.name
    assert notebook.trash_id == None
    assert notebook.read_write == False
    assert notebook.owner == False
    assert notebook.rank == None

    assert result.get( u"login_url" ) is None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert result[ u"groups" ] == []

  def test_current_after_signup_with_invite_id( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )

    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )

    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      signup_button = u"sign up",
      invite_id = invite_id,
    ) )

    invite_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]
    assert invite_notebook_id == self.notebooks[ 0 ].object_id

    user = self.__get_recent_user()
    assert isinstance( user, User )
    result = cherrypy.root.users.current( user.object_id )

    assert result[ u"user" ].object_id == user.object_id
    assert result[ u"user" ].username == self.new_username
    assert result[ u"user" ].email_address == self.new_email_address

    assert cherrypy.root.users.check_access( user.object_id, self.notebooks[ 0 ].object_id )
    assert cherrypy.root.users.check_access( user.object_id, self.notebooks[ 0 ].trash_id )

    # the notebook that the user was invited to should be in the list of returned notebooks
    notebooks = dict( [ ( notebook.object_id, notebook ) for notebook in result[ u"notebooks" ] ] )
    
    notebook = notebooks.get( invite_notebook_id )
    assert notebook
    assert notebook.revision
    assert notebook.name == self.notebooks[ 0 ].name
    assert notebook.trash_id
    assert notebook.read_write == False
    assert notebook.owner == False
    assert notebook.rank == 1

    notebook = notebooks.get( self.notebooks[ 0 ].trash_id )
    assert notebook.revision
    assert notebook.name == u"trash"
    assert notebook.trash_id == None
    assert notebook.read_write == False
    assert notebook.owner == False
    assert notebook.rank == None

    notebook = notebooks.get( self.anon_notebook.object_id )
    assert notebook.revision == self.anon_notebook.revision
    assert notebook.name == self.anon_notebook.name
    assert notebook.trash_id == None
    assert notebook.read_write == False
    assert notebook.owner == False
    assert notebook.rank == None

    assert result.get( u"login_url" ) is None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert result[ u"groups" ] == []

  def test_current_after_signup_with_rate_plan( self ):
    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      signup_button = u"sign up",
      rate_plan = u"2",
    ) )
    session_id = result[ u"session_id" ]

    assert result[ u"redirect" ] == u"/users/subscribe?rate_plan=2&yearly=False"

    user = self.__get_recent_user()
    assert isinstance( user, User )
    result = cherrypy.root.users.current( user.object_id )

    assert result[ u"user" ].object_id == user.object_id
    assert result[ u"user" ].username == self.new_username
    assert result[ u"user" ].email_address == self.new_email_address

    notebooks = result[ u"notebooks" ]
    notebook = notebooks[ 0 ]
    assert notebook.object_id == notebooks[ 1 ].trash_id
    assert notebook.revision
    assert notebook.name == u"trash"
    assert notebook.trash_id == None
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == None

    notebook = notebooks[ 1 ]
    assert notebook.object_id
    assert notebook.revision
    assert notebook.name == u"my notebook"
    assert notebook.trash_id
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    notebook = notebooks[ 2 ]
    assert notebook.object_id == self.anon_notebook.object_id
    assert notebook.revision == self.anon_notebook.revision
    assert notebook.name == self.anon_notebook.name
    assert notebook.trash_id == None
    assert notebook.read_write == False
    assert notebook.owner == False
    assert notebook.rank == None

    assert result.get( u"login_url" ) is None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert result[ u"groups" ] == []

  def test_signup_with_different_passwords( self ):
    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password + u"nomatch",
      email_address = self.new_email_address,
      signup_button = u"sign up",
    ) )

    assert result[ u"error" ]

  def test_signup_group_member( self ):
    self.login2()

    result = self.http_post( "/users/signup_group_member", dict(
      group_id = self.group.object_id,
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      create_user_button = u"create member",
    ), session_id = self.session_id )

    assert u"created" in result[ u"message" ]

    user = self.database.select_one( User, User.sql_load_by_username( self.new_username ) )
    assert user
    assert user.username == self.new_username
    assert user.email_address == self.new_email_address
    assert user.storage_bytes == 0
    assert user.group_storage_bytes == 0
    assert user.rate_plan == 1

    membership = cherrypy.root.users.check_group( user.object_id, self.group.object_id )
    assert membership is True

  def test_signup_group_member_without_access( self ):
    self.login2()

    result = self.http_post( "/users/signup_group_member", dict(
      group_id = self.group2.object_id,
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      create_user_button = u"create member",
    ), session_id = self.session_id )

    assert u"access" in result[ "error" ]
    user = self.database.select_one( User, User.sql_load_by_username( self.new_username ) )
    assert user is None

  def test_signup_group_member_without_admin_access( self ):
    self.login()

    result = self.http_post( "/users/signup_group_member", dict(
      group_id = self.group.object_id,
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      create_user_button = u"create member",
    ), session_id = self.session_id )

    assert u"access" in result[ "error" ]
    user = self.database.select_one( User, User.sql_load_by_username( self.new_username ) )
    assert user is None

  def test_signup_group_member_without_login( self ):
    result = self.http_post( "/users/signup_group_member", dict(
      group_id = self.group.object_id,
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      create_user_button = u"create member",
    ) )

    assert u"access" in result[ "error" ]
    user = self.database.select_one( User, User.sql_load_by_username( self.new_username ) )
    assert user is None

  def test_signup_group_member_with_invalid_rate_plan( self ):
    self.login2()

    self.user2.rate_plan = 17
    self.database.save( self.user2 )

    result = self.http_post( "/users/signup_group_member", dict(
      group_id = self.group.object_id,
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      create_user_button = u"create member",
    ), session_id = self.session_id )

    assert u"access" in result[ "error" ]
    user = self.database.select_one( User, User.sql_load_by_username( self.new_username ) )
    assert user is None

  def test_signup_group_member_without_user_admin_rate_plan( self ):
    self.login2()

    self.user2.rate_plan = 0
    self.database.save( self.user2 )

    result = self.http_post( "/users/signup_group_member", dict(
      group_id = self.group.object_id,
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      create_user_button = u"create member",
    ), session_id = self.session_id )

    assert u"access" in result[ "error" ]
    user = self.database.select_one( User, User.sql_load_by_username( self.new_username ) )
    assert user is None

  def test_signup_group_member_without_user_admin_rate_plan( self ):
    self.login2()

    self.user2.rate_plan = 0
    self.database.save( self.user2 )

    result = self.http_post( "/users/signup_group_member", dict(
      group_id = self.group.object_id,
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      create_user_button = u"create member",
    ), session_id = self.session_id )

    assert u"access" in result[ "error" ]
    user = self.database.select_one( User, User.sql_load_by_username( self.new_username ) )
    assert user is None

  def test_signup_group_member_without_included_users_in_rate_plan( self ):
    self.login2()

    del( self.settings[ u"global" ][ u"luminotes.rate_plans"][ 1 ][ u"included_users" ] )

    # first successfully create a group member
    result = self.http_post( "/users/signup_group_member", dict(
      group_id = self.group.object_id,
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      create_user_button = u"create member",
    ), session_id = self.session_id )

    assert u"access" in result[ "error" ]
    user = self.database.select_one( User, User.sql_load_by_username( self.new_username ) )
    assert user is None

  def test_signup_group_member_with_unknown_group( self ):
    self.login2()

    # first successfully create a group member
    result = self.http_post( "/users/signup_group_member", dict(
      group_id = u"unknowngroupid",
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      create_user_button = u"create member",
    ), session_id = self.session_id )

    assert u"access" in result[ "error" ]
    user = self.database.select_one( User, User.sql_load_by_username( self.new_username ) )
    assert user is None

  def test_signup_group_member_with_too_many_users( self ):
    self.login2()

    # first successfully create a group member
    self.http_post( "/users/signup_group_member", dict(
      group_id = self.group.object_id,
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      create_user_button = u"create member",
    ), session_id = self.session_id )

    # then create another, going over the limit of the rate plan's included_users
    result = self.http_post( "/users/signup_group_member", dict(
      group_id = self.group.object_id,
      username = u"kaylee",
      password = u"reallyshiny",
      password_repeat = u"reallyshiny",
      email_address = u"mechanic@example.com",
      create_user_button = u"create member",
    ), session_id = self.session_id )

    assert u"additional users" in result[ "error" ]
    user = self.database.select_one( User, User.sql_load_by_username( u"kaylee" ) )
    assert user is None

  def test_subscribe( self ):
    self.login()

    result = self.http_post( "/users/subscribe", dict(
      rate_plan = u"1",
    ), session_id = self.session_id )

    form = result.get( u"form" )
    plan = self.settings[ u"global" ][ u"luminotes.rate_plans" ][ 1 ]

    assert form == plan[ u"button" ] % self.user.object_id

  def test_subscribe_yearly( self ):
    self.login()

    result = self.http_post( "/users/subscribe", dict(
      rate_plan = u"1",
      yearly = True,
    ), session_id = self.session_id )

    form = result.get( u"form" )
    plan = self.settings[ u"global" ][ u"luminotes.rate_plans" ][ 1 ]

    assert form == plan[ u"yearly_button" ] % self.user.object_id

  def test_subscribe_with_free_rate_plan( self ):
    self.login()

    result = self.http_post( "/users/subscribe", dict(
      rate_plan = u"0",
    ), session_id = self.session_id )

    assert u"plan" in result[ u"error" ]
    assert u"invalid" in result[ u"error" ]

  def test_subscribe_with_invalid_rate_plan( self ):
    self.login()

    result = self.http_post( "/users/subscribe", dict(
      rate_plan = u"17",
    ), session_id = self.session_id )

    assert u"plan" in result[ u"error" ]
    assert u"invalid" in result[ u"error" ]

  def test_subscribe_without_login( self ):
    result = self.http_post( "/users/subscribe", dict(
      rate_plan = u"1",
    ) )

    assert u"user" in result[ u"error" ]
    assert u"invalid" in result[ u"error" ]

  def test_subscribe_without_subscribe_button( self ):
    self.login()
    self.settings[ u"global" ][ u"luminotes.rate_plans" ][ 1 ][ u"button" ] = u"  "

    result = self.http_post( "/users/subscribe", dict(
      rate_plan = u"1",
    ), session_id = self.session_id )

    assert u"not configured" in result[ u"error" ]

  def test_demo( self ):
    result = self.http_post( "/users/demo", dict() )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

  def test_current_after_demo( self ):
    result = self.http_post( "/users/demo", dict() )
    session_id = result[ u"session_id" ]

    new_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]

    user = self.__get_recent_user()
    assert isinstance( user, User )
    result = cherrypy.root.users.current( user.object_id )

    assert result[ u"user" ].object_id == user.object_id
    assert result[ u"user" ].username is None
    assert result[ u"user" ].email_address is None

    notebooks = result[ u"notebooks" ]
    assert len( notebooks ) == 3
    notebook = notebooks[ 0 ]
    assert notebook.object_id == notebooks[ 1 ].trash_id
    assert notebook.revision
    assert notebook.name == u"trash"
    assert notebook.trash_id == None
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == None

    notebook = notebooks[ 1 ]
    assert notebook.object_id == new_notebook_id
    assert notebook.revision
    assert notebook.name == u"my notebook"
    assert notebook.trash_id
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    notebook = notebooks[ 2 ]
    assert notebook.object_id == self.anon_notebook.object_id
    assert notebook.revision == self.anon_notebook.revision
    assert notebook.name == self.anon_notebook.name
    assert notebook.trash_id == None
    assert notebook.read_write == False
    assert notebook.owner == False
    assert notebook.rank == None

    assert result.get( u"login_url" ) is None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert result[ u"groups" ] == []

  def test_current_after_demo_twice( self ):
    result = self.http_post( "/users/demo", dict() )
    session_id = result[ u"session_id" ]

    new_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]

    user = self.__get_recent_user()
    assert isinstance( user, User )
    result = cherrypy.root.users.current( user.object_id )

    user_id = result[ u"user" ].object_id
    assert user_id == user.object_id

    # request a demo for a second time
    result = self.http_post( "/users/demo", dict(), session_id = session_id )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )
    notebook_id_again = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]

    assert notebook_id_again == new_notebook_id

    result = cherrypy.root.users.current( user_id )

    user_id_again = result[ u"user" ].object_id

    # since we're already logged in as a guest user with a demo notebook, requesting a demo again
    # should just use the same guest user with the same notebook
    assert user_id_again == user_id

  def test_login( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username,
      password = self.password,
      login_button = u"login",
    ) )

    assert result[ u"redirect" ] == u"/notebooks/%s" % self.notebooks[ 0 ].object_id

  def test_login_with_unknown_user( self ):
    result = self.http_post( "/users/login", dict(
      username = u"nosuchuser",
      password = self.password,
      login_button = u"login",
    ) )

    assert result[ u"error" ]

  def test_login_with_invalid_password( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username,
      password = u"wrongpass",
      login_button = u"login",
    ) )

    assert result[ u"error" ]

  def test_logout( self ):
    result = self.http_post( "/users/logout", dict() )

    assert result[ u"redirect" ] == self.settings[ u"global" ].get( u"luminotes.http_url" ) + u"/"

  def test_current( self ):
    result = cherrypy.root.users.current( self.user.object_id )

    assert result[ u"user" ]
    assert result[ u"user" ].object_id == self.user.object_id
    assert result[ u"user" ].username == self.user.username
    assert len( result[ u"notebooks" ] ) == 5
    assert result[ u"notebooks" ][ 0 ].object_id
    assert result[ u"notebooks" ][ 0 ].name == u"trash"
    assert result[ u"notebooks" ][ 0 ].read_write == True
    assert result[ u"notebooks" ][ 0 ].owner == True
    assert result[ u"notebooks" ][ 0 ].rank == None
    assert result[ u"notebooks" ][ 1 ].object_id
    assert result[ u"notebooks" ][ 1 ].name == u"trash"
    assert result[ u"notebooks" ][ 1 ].read_write == True
    assert result[ u"notebooks" ][ 1 ].owner == True
    assert result[ u"notebooks" ][ 1 ].rank == None
    assert result[ u"notebooks" ][ 2 ].object_id == self.notebooks[ 0 ].object_id
    assert result[ u"notebooks" ][ 2 ].name == self.notebooks[ 0 ].name
    assert result[ u"notebooks" ][ 2 ].read_write == True
    assert result[ u"notebooks" ][ 2 ].owner == True
    assert result[ u"notebooks" ][ 2 ].rank == 0
    assert result[ u"notebooks" ][ 3 ].object_id == self.notebooks[ 1 ].object_id
    assert result[ u"notebooks" ][ 3 ].name == self.notebooks[ 1 ].name
    assert result[ u"notebooks" ][ 3 ].read_write == True
    assert result[ u"notebooks" ][ 3 ].owner == True
    assert result[ u"notebooks" ][ 3 ].rank == 1
    assert result[ u"notebooks" ][ 4 ].object_id == self.anon_notebook.object_id
    assert result[ u"notebooks" ][ 4 ].name == self.anon_notebook.name
    assert result[ u"notebooks" ][ 4 ].read_write == False
    assert result[ u"notebooks" ][ 4 ].owner == False
    assert result[ u"notebooks" ][ 4 ].rank == None
    assert result[ u"login_url" ] is None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert result[ u"groups" ]
    assert result[ u"groups" ][ 0 ].object_id == self.group.object_id
    assert result[ u"groups" ][ 0 ].name == self.group.name
    assert result[ u"groups" ][ 0 ].admin == False

  def test_current_anonymous( self ):
    result = cherrypy.root.users.current( self.anonymous.object_id )

    assert result[ u"user" ].username == "anonymous"
    assert len( result[ u"notebooks" ] ) == 1
    assert result[ u"notebooks" ][ 0 ].object_id == self.anon_notebook.object_id
    assert result[ u"notebooks" ][ 0 ].name == self.anon_notebook.name
    assert result[ u"notebooks" ][ 0 ].read_write == False
    assert result[ u"notebooks" ][ 0 ].owner == False
    assert result[ u"notebooks" ][ 0 ].rank == None

    login_note = self.database.select_one( Note, self.anon_notebook.sql_load_note_by_title( u"login" ) )
    assert result[ u"login_url" ] == u"%s/notebooks/%s?note_id=%s" % (
      self.settings[ u"global" ][ u"luminotes.https_url" ],
      self.anon_notebook.object_id,
      login_note.object_id,
    )
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert result[ u"groups" ] == []

  def test_login_with_invite_id( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )

    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )

    result = self.http_post( "/users/login", dict(
      username = self.username2,
      password = self.password2,
      invite_id = invite_id,
      login_button = u"login",
    ) )

    invite_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]
    assert invite_notebook_id == self.notebooks[ 0 ].object_id

    assert cherrypy.root.users.check_access( self.user2.object_id, self.notebooks[ 0 ].object_id )
    assert cherrypy.root.users.check_access( self.user2.object_id, self.notebooks[ 0 ].trash_id )

  def test_login_with_after_login( self ):
    after_login = u"/foo/bar"

    result = self.http_post( "/users/login", dict(
      username = self.username2,
      password = self.password2,
      after_login = after_login,
      login_button = u"login",
    ) )

    assert result[ u"redirect" ] == after_login

  def test_login_with_after_login_with_full_url( self ):
    after_login = u"http://this_url/does/not/start/with/a/slash"

    result = self.http_post( "/users/login", dict(
      username = self.username2,
      password = self.password2,
      after_login = after_login,
      login_button = u"login",
    ) )

    assert result[ u"redirect" ] == u"/"

  def test_update_storage( self ):
    previous_revision = self.user.revision

    cherrypy.root.users.update_storage( self.user.object_id )

    expected_size = cherrypy.root.users.calculate_storage( self.user )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == expected_size
    assert user.group_storage_bytes == 0
    assert user.revision > previous_revision

  def test_update_storage_with_unknown_user_id( self ):
    original_revision = self.user.revision

    cherrypy.root.users.update_storage( 77 )

    expected_size = cherrypy.root.users.calculate_storage( self.user )

    user = self.database.load( User, self.user.object_id )
    assert self.user.storage_bytes == 0
    assert self.user.group_storage_bytes == 0
    assert self.user.revision == original_revision

  def test_update_storage_without_quota( self ):
    self.settings[ u"global" ][ u"luminotes.rate_plans" ][ 0 ][ u"storage_bytes" ] = None
    previous_revision = self.user.revision

    cherrypy.root.users.update_storage( self.user.object_id )

    expected_size = cherrypy.root.users.calculate_storage( self.user )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == expected_size
    assert user.group_storage_bytes == 0
    assert user.revision > previous_revision

  def test_check_access( self ):
    access = cherrypy.root.users.check_access( self.user.object_id, self.notebooks[ 0 ].object_id )

    assert access is True

  def test_check_access_read_write( self ):
    access = cherrypy.root.users.check_access( self.user.object_id, self.notebooks[ 0 ].object_id, read_write = True )

    assert access is True

  def test_check_access_owner( self ):
    access = cherrypy.root.users.check_access( self.user.object_id, self.notebooks[ 0 ].object_id, owner = True )

    assert access is True

  def test_check_access_full( self ):
    access = cherrypy.root.users.check_access( self.user.object_id, self.notebooks[ 0 ].object_id, read_write = True, owner = True )

    assert access is True

  def test_check_access_anon( self ):
    access = cherrypy.root.users.check_access( self.user.object_id, self.anon_notebook.object_id )

    assert access is True

  def test_check_access_anon_read_write( self ):
    access = cherrypy.root.users.check_access( self.user.object_id, self.anon_notebook.object_id, read_write = True )

    assert access is False

  def test_check_access_anon_owner( self ):
    access = cherrypy.root.users.check_access( self.user.object_id, self.anon_notebook.object_id, owner = True )

    assert access is False

  def test_check_access_anon_full( self ):
    access = cherrypy.root.users.check_access( self.user.object_id, self.anon_notebook.object_id, read_write = True, owner = True )

    assert access is False

  def test_check_group( self ):
    membership = cherrypy.root.users.check_group( self.user.object_id, self.group.object_id )

    assert membership is True

  def test_check_group_with_admin( self ):
    membership = cherrypy.root.users.check_group( self.user2.object_id, self.group.object_id )

    assert membership is True

  def test_check_group_anon( self ):
    membership = cherrypy.root.users.check_group( self.anonymous.object_id, self.group.object_id )

    assert membership is False

  def test_check_group_without_membership( self ):
    membership = cherrypy.root.users.check_group( self.user.object_id, self.group2.object_id )

    assert membership is False

  def test_check_group_without_user( self ):
    membership = cherrypy.root.users.check_group( None, self.group2.object_id )

    assert membership is False

  def test_check_group_admin( self ):
    membership = cherrypy.root.users.check_group( self.user.object_id, self.group.object_id, admin = True )

    assert membership is False

  def test_check_group_admin_with_admin( self ):
    membership = cherrypy.root.users.check_group( self.user2.object_id, self.group.object_id, admin = True )

    assert membership is True

  def test_remove_group( self ):
    self.login2()

    self.user.rate_plan = 1
    self.database.save( self.user )

    result = self.http_post( "/users/remove_group", dict(
      user_id_to_remove = self.user.object_id,
      group_id = self.group.object_id,
    ), session_id = self.session_id )

    assert u"revoked" in result[ u"message" ]
    assert cherrypy.root.users.check_group( self.user.object_id, self.group.object_id ) == False

    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

  def test_remove_group_without_access( self ):
    self.login2()

    self.user.rate_plan = 1
    self.database.save( self.user )

    result = self.http_post( "/users/remove_group", dict(
      user_id_to_remove = self.user.object_id,
      group_id = self.group2.object_id,
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]
    assert cherrypy.root.users.check_group( self.user.object_id, self.group.object_id ) == True

    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

  def test_remove_group_without_admin_access( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    result = self.http_post( "/users/remove_group", dict(
      user_id_to_remove = self.user.object_id,
      group_id = self.group.object_id,
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]
    assert cherrypy.root.users.check_group( self.user.object_id, self.group.object_id ) == True

    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

  def test_remove_group_with_unknown_group( self ):
    self.login2()

    self.user.rate_plan = 1
    self.database.save( self.user )

    result = self.http_post( "/users/remove_group", dict(
      user_id_to_remove = self.user.object_id,
      group_id = u"unknowngroupid",
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]
    assert cherrypy.root.users.check_group( self.user.object_id, self.group.object_id ) == True

    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

  def test_remove_group_with_unknown_user( self ):
    self.login2()

    self.user.rate_plan = 1
    self.database.save( self.user )

    result = self.http_post( "/users/remove_group", dict(
      user_id_to_remove = u"unknownuserid",
      group_id = self.group.object_id,
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]
    assert cherrypy.root.users.check_group( self.user.object_id, self.group.object_id ) == True

    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

  def test_send_reset( self ):
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
    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert result[ u"user" ].username == "anonymous"
    assert len( result[ u"notebooks" ] ) == 1
    assert result[ u"notebooks" ][ 0 ].object_id == self.anon_notebook.object_id
    assert result[ u"notebooks" ][ 0 ].name == self.anon_notebook.name
    assert result[ u"notebooks" ][ 0 ].read_write == False
    assert result[ u"notebooks" ][ 0 ].owner == False
    assert result[ u"notebooks" ][ 0 ].rank == None

    login_note = self.database.select_one( Note, self.anon_notebook.sql_load_note_by_title( u"login" ) )
    assert result[ u"login_url" ] == u"%s/notebooks/%s?note_id=%s" % (
      self.settings[ u"global" ][ u"luminotes.https_url" ],
      self.anon_notebook.object_id,
      login_note.object_id,
    )
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert result[ u"notes" ][ 0 ].title == u"complete your password reset"
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"password reset" in result[ u"notes" ][ 0 ].contents
    assert self.user.username in result[ u"notes" ][ 0 ].contents
    assert self.user2.username in result[ u"notes" ][ 0 ].contents

  def test_redeem_reset_unknown( self ):
    password_reset_id = u"unknownresetid"
    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert u"expired" in result[ u"error" ]

  def test_redeem_reset_expired( self ):
    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    # to trigger expiration, pretend that the password reset was made 26 hours ago
    password_reset = self.database.load( Password_reset, password_reset_id )
    password_reset._Persistent__revision = datetime.now( tz = utc ) - timedelta( hours = 26 )
    self.database.save( password_reset )

    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert u"expired" in result[ u"error" ]

  def test_redeem_reset_already_redeemed( self ):
    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    password_reset = self.database.load( Password_reset, password_reset_id )
    password_reset.redeemed = True
    self.database.save( password_reset )

    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert u"already" in result[ u"error" ]

  def test_redeem_reset_unknown_email( self ):
    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    password_reset = self.database.load( Password_reset, password_reset_id )
    password_reset._Password_reset__email_address = u"unknown@example.com"
    self.database.save( password_reset )

    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert u"email address" in result[ u"error" ]

  def test_reset_password( self ):
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

    assert result[ u"redirect" ]

    # check that the password reset is now marked as redeemed
    password_reset = self.database.load( Password_reset, password_reset_id )
    assert password_reset.redeemed

    # check that the password was actually reset for one of the users, but not the other
    user = self.database.load( User, self.user.object_id )
    assert user.check_password( new_password )
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.check_password( self.password2 )

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

    assert u"expired" in result[ "error" ]

    # check that neither user's password has changed
    user = self.database.load( User, self.user.object_id )
    assert user.check_password( self.password )
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.check_password( self.password2 )

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

    assert u"valid" in result[ "error" ]

    # check that neither user's password has changed
    user = self.database.load( User, self.user.object_id )
    assert user.check_password( self.password )
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.check_password( self.password2 )

  def test_reset_password_expired( self ):
    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    # to trigger expiration, pretend that the password reset was made 26 hours ago
    password_reset = self.database.load( Password_reset, password_reset_id )
    password_reset._Persistent__revision = datetime.now( tz = utc ) - timedelta( hours = 26 )
    self.database.save( password_reset )

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
    password_reset = self.database.load( Password_reset, password_reset_id )
    assert password_reset.redeemed == False

    assert u"expired" in result[ "error" ]

    # check that neither user's password has changed
    user = self.database.load( User, self.user.object_id )
    assert user.check_password( self.password )
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.check_password( self.password2 )

  def test_reset_password_non_matching( self ):
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

    assert u"password" in result[ "error" ]

    # check that neither user's password has changed
    user = self.database.load( User, self.user.object_id )
    assert user.check_password( self.password )
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.check_password( self.password2 )

  def test_reset_password_blank( self ):
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

    assert result[ "error" ]

    # check that neither user's password has changed
    assert self.user.check_password( self.password )
    assert self.user2.check_password( self.password2 )

  def test_reset_password_multiple_users( self ):
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

    assert result[ u"redirect" ]

    # check that the password reset is now marked as redeemed
    password_reset = self.database.load( Password_reset, password_reset_id )
    assert password_reset.redeemed

    # check that the password was actually reset for both users
    user = self.database.load( User, self.user.object_id )
    assert user.check_password( new_password )
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.check_password( new_password2 )

  def test_send_invites( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert u"An invitation has been sent." in result[ u"message" ]
    invites = result[ u"invites" ]
    assert len( invites ) == 1
    invite = invites[ -1 ]
    assert invite
    assert invite.read_write is False
    assert invite.owner is False

    assert smtplib.SMTP.connected == False
    assert len( smtplib.SMTP.emails ) == 1

    ( from_address, to_addresses, message ) = smtplib.SMTP.emails[ 0 ]
    assert self.email_address in from_address
    assert to_addresses == email_addresses_list
    assert self.notebooks[ 0 ].name in message
    matches = self.INVITE_LINK_PATTERN.search( message )
    invite_id = matches.group( 2 )
    assert invite_id

    # assert that the invite has the read_write / owner flags set appropriately
    invite = self.database.load( Invite, invite_id )
    assert invite
    assert invite.read_write is False
    assert invite.owner is False

  def test_send_invites_with_unicode_notebook_name( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    self.notebooks[ 0 ].name = u"\xe4"
    quoted_printable_notebook_name = u"=C3=A4"
    self.database.save( self.notebooks[ 0 ] )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert u"An invitation has been sent." in result[ u"message" ]
    invites = result[ u"invites" ]
    assert len( invites ) == 1
    invite = invites[ -1 ]
    assert invite
    assert invite.read_write is False
    assert invite.owner is False

    assert smtplib.SMTP.connected == False
    assert len( smtplib.SMTP.emails ) == 1

    from email.Message import Message
    from email import Charset
    ( from_address, to_addresses, message ) = smtplib.SMTP.emails[ 0 ]

    assert self.email_address in from_address
    assert to_addresses == email_addresses_list
    assert u'Content-Type: text/plain; charset="utf-8"' in message
    assert u'Content-Transfer-Encoding: quoted-printable' in message
    assert quoted_printable_notebook_name in message
    matches = self.INVITE_LINK_PATTERN.search( message )
    invite_id = matches.group( 2 )
    assert invite_id

    # assert that the invite has the read_write / owner flags set appropriately
    invite = self.database.load( Invite, invite_id )
    assert invite
    assert invite.read_write is False
    assert invite.owner is False

  def test_send_invites_collaborator( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"collaborator",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert u"An invitation has been sent." in result[ u"message" ]
    invites = result[ u"invites" ]
    assert len( invites ) == 1
    invite = invites[ -1 ]
    assert invite
    assert invite.read_write is True
    assert invite.owner is False

    assert smtplib.SMTP.connected == False
    assert len( smtplib.SMTP.emails ) == 1

    ( from_address, to_addresses, message ) = smtplib.SMTP.emails[ 0 ]
    assert self.email_address in from_address
    assert to_addresses == email_addresses_list
    assert self.notebooks[ 0 ].name in message
    matches = self.INVITE_LINK_PATTERN.search( message )
    invite_id = matches.group( 2 )
    assert invite_id

    # assert that the invite has the read_write / owner flags set appropriately
    invite = self.database.load( Invite, invite_id )
    assert invite
    assert invite.read_write is True
    assert invite.owner is False

  def test_send_invites_owner( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"owner",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert u"An invitation has been sent." in result[ u"message" ]
    invites = result[ u"invites" ]
    assert len( invites ) == 1
    invite = invites[ -1 ]
    assert invite
    assert invite.read_write is True
    assert invite.owner is True

    assert smtplib.SMTP.connected == False
    assert len( smtplib.SMTP.emails ) == 1

    ( from_address, to_addresses, message ) = smtplib.SMTP.emails[ 0 ]
    assert self.email_address in from_address
    assert to_addresses == email_addresses_list
    assert self.notebooks[ 0 ].name in message
    matches = self.INVITE_LINK_PATTERN.search( message )
    invite_id = matches.group( 2 )
    assert invite_id

    # assert that the invite has the read_write / owner flags set appropriately
    invite = self.database.load( Invite, invite_id )
    assert invite
    assert invite.read_write is True
    assert invite.owner is True

  def test_send_invites_multiple( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com", u"bar@example.com", u"baz@example.com" ]
    email_addresses = u"Bob <%s>,%s\n %s  " % \
      ( email_addresses_list[ 0 ], email_addresses_list[ 1 ], email_addresses_list[ 2 ] )

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    email_count = len( email_addresses_list )
    invites = result[ u"invites" ]
    assert len( invites ) == email_count
    for invite in invites:
      assert invite
      assert invite.read_write is False
      assert invite.owner is False

    assert u"%s invitations have been sent." % email_count in result[ u"message" ]
    assert smtplib.SMTP.connected == False
    assert len( smtplib.SMTP.emails ) == email_count

    for ( from_address, to_addresses, message ) in smtplib.SMTP.emails:
      assert self.email_address in from_address
      assert len( to_addresses ) == 1
      assert to_addresses[ 0 ] in email_addresses_list
      email_addresses_list.remove( to_addresses[ 0 ] )
      assert self.notebooks[ 0 ].name in message
      assert self.INVITE_LINK_PATTERN.search( message )

  def test_send_invites_duplicate( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com", u"bar@example.com", u"foo@example.com" ]
    email_addresses = u" %s N.E. One <%s>,\n%s" % \
      ( email_addresses_list[ 0 ], email_addresses_list[ 1 ], email_addresses_list[ 2 ] )

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    email_count = len( email_addresses_list ) - 1 # -1 because of the duplicate
    invites = result[ u"invites" ]
    assert len( invites ) == email_count
    for invite in invites:
      assert invite
      assert invite.read_write is False
      assert invite.owner is False
    
    assert u"%s invitations have been sent." % email_count in result[ u"message" ]
    assert smtplib.SMTP.connected == False
    assert len( smtplib.SMTP.emails ) == email_count

    for ( from_address, to_addresses, message ) in smtplib.SMTP.emails:
      assert self.email_address in from_address
      assert len( to_addresses ) == 1
      assert to_addresses[ 0 ] in email_addresses_list
      email_addresses_list.remove( to_addresses[ 0 ] )
      assert self.notebooks[ 0 ].name in message
      assert self.INVITE_LINK_PATTERN.search( message )

  def test_send_invites_similar( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    # first send an invite with read_write and owner set to False
    self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )

    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id1 = matches.group( 2 )
    assert invite_id1

    # login as another user and redeem the invite
    self.login2()
    result = self.http_post( "/users/redeem_invite", dict(
      invite_id = invite_id1,
    ), session_id = self.session_id )

    # then send a similar invite to the same email address with read_write and owner set to True
    self.login()
    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"owner",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    
    invites = result[ u"invites" ]
    assert len( invites ) == 2
    invite = invites[ 0 ]
    assert invite
    assert invite.read_write is True
    assert invite.owner is True
    invite = invites[ 1 ]
    assert invite
    assert invite.read_write is True
    assert invite.owner is True

    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id2 = matches.group( 2 )
    assert invite_id2

    # assert that both invites have the read_write / owner flags set to True now
    invite1 = self.database.load( Invite, invite_id1 )
    assert invite1
    assert invite1.read_write is True
    assert invite1.owner is True

    invite2 = self.database.load( Invite, invite_id2 )
    assert invite2
    assert invite2.read_write is True
    assert invite2.owner is True

    # assert that the user_notebook table has also been updated accordingly
    access = self.database.select_one( bool, self.user2.sql_has_access(
      self.notebooks[ 0 ].object_id,
      read_write = True,
      owner = True,
    ) )
    assert access is True
    access = self.database.select_one( bool, self.user2.sql_has_access(
      self.notebooks[ 0 ].trash_id,
      read_write = True,
      owner = True,
    ) )
    assert access is True

  def test_send_invites_similar_downgrade( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    # first send an invite with read_write and owner set to False
    self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"collaborator",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    
    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id1 = matches.group( 2 )
    assert invite_id1

    # login as another user and redeem the invite
    self.login2()
    result = self.http_post( "/users/redeem_invite", dict(
      invite_id = invite_id1,
    ), session_id = self.session_id )

    # then send a similar invite to the same email address with read_write and owner set to False
    self.login()
    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    
    print result
    invites = result[ u"invites" ]
    assert len( invites ) == 2
    invite = invites[ 0 ]
    assert invite
    assert invite.read_write is False
    assert invite.owner is False
    invite = invites[ 1 ]
    assert invite
    assert invite.read_write is False
    assert invite.owner is False

    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id2 = matches.group( 2 )
    assert invite_id2

    # assert that both invites have the read_write / owner flags set to False now
    invite1 = self.database.load( Invite, invite_id1 )
    assert invite1
    assert invite1.read_write is False
    assert invite1.owner is False

    invite2 = self.database.load( Invite, invite_id2 )
    assert invite2
    assert invite2.read_write is False
    assert invite2.owner is False

    # assert that the user_notebook table has also been updated accordingly
    access = self.database.select_one( bool, self.user2.sql_has_access(
      self.notebooks[ 0 ].object_id,
      read_write = False,
      owner = False,
    ) )
    assert access is True
    access = self.database.select_one( bool, self.user2.sql_has_access(
      self.notebooks[ 0 ].trash_id,
      read_write = False,
      owner = False,
    ) )
    assert access is True

  def test_send_invites_with_generic_from_address( self ):
    self.login()

    # setting the user's email address to None means the invite will be sent
    # with a "generic" From address (in this case, Luminotes support)
    self.user._User__email_address = None
    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    invites = result[ u"invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite
    assert invite.read_write is False
    assert invite.owner is False
    
    assert u"An invitation has been sent." in result[ u"message" ]
    assert smtplib.SMTP.connected == False
    assert len( smtplib.SMTP.emails ) == 1

    ( from_address, to_addresses, message ) = smtplib.SMTP.emails[ 0 ]
    assert self.settings[ u"global" ][ u"luminotes.support_email" ] in from_address
    assert to_addresses == email_addresses_list
    assert self.notebooks[ 0 ].name in message
    assert self.INVITE_LINK_PATTERN.search( message )

  def test_send_invites_without_login( self ):
    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert result[ u"error" ]
    assert "access" in result[ u"error" ]

  def test_send_invites_too_short( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert result[ u"error" ]

  def test_send_invites_too_long( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"x" * 5001 ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert result[ u"error" ]

  def test_send_invites_no_addresses( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"this is not an @email address!" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert result[ u"error" ]

  def test_send_invites_without_username( self ):
    self.login()

    self.user._User__username = None
    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert result[ u"error" ]
    assert "access" in result[ u"error" ]

  def test_send_invites_without_any_access( self ):
    self.login2()

    self.user2.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert result[ u"error" ]
    assert "access" in result[ u"error" ]

  def test_send_invites_without_read_write_access( self ):
    self.login()

    self.database.execute( self.user.sql_update_access( self.notebooks[ 0 ].object_id, read_write = False, owner = True ) )
    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert result[ u"error" ]
    assert "access" in result[ u"error" ]

  def test_send_invites_without_owner_access( self ):
    self.login()

    self.database.execute( self.user.sql_update_access( self.notebooks[ 0 ].object_id, read_write = True, owner = False ) )
    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert result[ u"error" ]
    assert "access" in result[ u"error" ]

  def test_send_invites_viewer_with_lowest_rate_plan( self ):
    self.login()

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    invites = result[ u"invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite
    assert invite.read_write is False
    assert invite.owner is False
    
    assert u"An invitation has been sent." in result[ u"message" ]
    assert smtplib.SMTP.connected == False
    assert len( smtplib.SMTP.emails ) == 1

    ( from_address, to_addresses, message ) = smtplib.SMTP.emails[ 0 ]
    assert self.email_address in from_address
    assert to_addresses == email_addresses_list
    assert self.notebooks[ 0 ].name in message
    assert self.INVITE_LINK_PATTERN.search( message )

  def test_send_invites_collaborator_with_lowest_rate_plan( self ):
    self.login()

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"collaborator",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert result[ u"error" ]
    assert "access" in result[ u"error" ]

  def test_send_invites_owner_with_lowest_rate_plan( self ):
    self.login()

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"owner",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert result[ u"error" ]
    assert "access" in result[ u"error" ]

  def test_send_invites_with_unknown_notebook( self ):
    self.login()

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]
    unknown_notebook_id = u"neverheardofit"

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = unknown_notebook_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    session_id = result[ u"session_id" ]
    
    assert result[ u"error" ]
    assert "access" in result[ u"error" ]

  def test_revoke_invite( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    
    assert len( result[ u"invites" ] ) == 1
    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )

    result = self.http_post( "/users/revoke_invite", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      invite_id = invite_id,
    ), session_id = self.session_id )

    assert result[ u"message" ]
    assert len( result[ u"invites" ] ) == 0

  def test_revoke_invite_multiple( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com", u"bar@example.com", u"foo@example.com" ]
    email_addresses = u" ".join( email_addresses_list )

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    
    assert len( result[ u"invites" ] ) == 2
    ( from_address, to_addresses, message ) = smtplib.SMTP.emails[ 0 ]
    matches = self.INVITE_LINK_PATTERN.search( message )
    invite_id = matches.group( 2 )

    result = self.http_post( "/users/revoke_invite", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      invite_id = invite_id,
    ), session_id = self.session_id )

    assert result[ u"message" ]
    assert len( result[ u"invites" ] ) == 1
    assert result[ u"invites" ][ 0 ].email_address == email_addresses_list[ 1 ]

  def test_revoke_invite_redeemed( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    
    assert len( result[ u"invites" ] ) == 1
    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )

    self.login2()
    result = self.http_post( "/users/redeem_invite", dict(
      invite_id = invite_id,
    ), session_id = self.session_id )

    assert cherrypy.root.users.check_access( self.user2.object_id, self.notebooks[ 0 ].object_id )
    assert cherrypy.root.users.check_access( self.user2.object_id, self.notebooks[ 0 ].trash_id )

    self.login()
    result = self.http_post( "/users/revoke_invite", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      invite_id = invite_id,
    ), session_id = self.session_id )

    assert result[ u"message" ]
    assert len( result[ u"invites" ] ) == 0

    assert not cherrypy.root.users.check_access( self.user2.object_id, self.notebooks[ 0 ].object_id )
    assert not cherrypy.root.users.check_access( self.user2.object_id, self.notebooks[ 0 ].trash_id )

  def test_revoke_invite_redeemed_self( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"owner",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    
    assert len( result[ u"invites" ] ) == 1
    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )

    self.login2()
    result = self.http_post( "/users/redeem_invite", dict(
      invite_id = invite_id,
    ), session_id = self.session_id )

    assert cherrypy.root.users.check_access( self.user2.object_id, self.notebooks[ 0 ].object_id )
    assert cherrypy.root.users.check_access( self.user2.object_id, self.notebooks[ 0 ].trash_id )

    # as user2, revoke that user's own invite
    result = self.http_post( "/users/revoke_invite", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      invite_id = invite_id,
    ), session_id = self.session_id )

    assert result[ u"message" ]
    assert len( result[ u"invites" ] ) == 0

    # the user should no longer have any access
    assert not cherrypy.root.users.check_access( self.user2.object_id, self.notebooks[ 0 ].object_id )
    assert not cherrypy.root.users.check_access( self.user2.object_id, self.notebooks[ 0 ].trash_id )

  def test_revoke_invite_without_login( self ):
    # login to send the invites, but don't send the logged-in session id for revoke_invite() below
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )

    assert len( result[ u"invites" ] ) == 1
    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )

    result = self.http_post( "/users/revoke_invite", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      invite_id = invite_id,
    ) )

    assert result[ u"error" ]
    assert "access" in result[ u"error" ]

  def test_revoke_invite_unknown( self ):
    self.login()

    invite_id = u"unknowninviteid"

    result = self.http_post( "/users/revoke_invite", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      invite_id = invite_id,
    ), session_id = self.session_id )

    assert result[ u"error" ]
    assert "access" in result[ u"error" ]

  def test_revoke_invite_for_incorrect_notebook( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    result = self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    
    assert len( result[ u"invites" ] ) == 1
    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )

    result = self.http_post( "/users/revoke_invite", dict(
      notebook_id = self.notebooks[ 1 ].object_id,
      invite_id = invite_id,
    ), session_id = self.session_id )

    assert result[ u"error" ]
    assert "access" in result[ u"error" ]

  def test_redeem_invite( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )

    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )
    
    result = self.http_post( "/users/redeem_invite", dict(
      invite_id = invite_id,
    ) )

    # assert that a redeem invite page is returned with sign up / login links
    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert result[ u"notebook" ].name == self.anon_notebook.name
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"total_notes_count" ] == 1
    assert result[ u"note_read_write" ] == False
    assert len( result[ u"notes" ] ) == 1
    assert result[ u"notes" ][ 0 ].object_id == "redeem_invite"
    assert u"sign up" in result[ u"notes" ][ 0 ].contents
    assert u"login" in result[ u"notes" ][ 0 ].contents
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert len( result[ u"invites" ] ) == 0

  def test_redeem_invite_unknown( self ):
    result = self.http_post( "/users/redeem_invite", dict(
      invite_id = "unknowninviteid",
    ) )

    assert result[ u"error" ]
    assert u"unknown" in result[ u"error" ]

  def test_redeem_invite_after_login( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )

    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )

    self.login2()
    
    result = self.http_post( "/users/redeem_invite", dict(
      invite_id = invite_id,
    ), session_id = self.session_id )

    # assert that access has been granted
    assert cherrypy.root.users.check_access( self.user2.object_id, self.notebooks[ 0 ].object_id )
    assert cherrypy.root.users.check_access( self.user2.object_id, self.notebooks[ 0 ].trash_id )

    # assert that the user is redirected to the notebook that the invite is for
    assert result[ u"redirect"].startswith( u"/notebooks/" )
    notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]
    assert notebook_id == self.notebooks[ 0 ].object_id

  def test_redeem_invite_after_login_already_redeemed( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )

    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )

    self.login2()
    
    self.http_post( "/users/redeem_invite", dict(
      invite_id = invite_id,
    ), session_id = self.session_id )

    result = self.http_post( "/users/redeem_invite", dict(
      invite_id = invite_id,
    ), session_id = self.session_id )

    # assert that access is still granted
    assert cherrypy.root.users.check_access( self.user2.object_id, self.notebooks[ 0 ].object_id )
    assert cherrypy.root.users.check_access( self.user2.object_id, self.notebooks[ 0 ].trash_id )

    # assert that the user is redirected to the notebook that the invite is for
    assert result[ u"redirect"].startswith( u"/notebooks/" )
    notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]
    assert notebook_id == self.notebooks[ 0 ].object_id

  def test_redeem_invite_after_login_already_redeemed_by_different_user( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )

    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )

    self.login2()
    
    self.http_post( "/users/redeem_invite", dict(
      invite_id = invite_id,
    ), session_id = self.session_id )

    self.login()

    result = self.http_post( "/users/redeem_invite", dict(
      invite_id = invite_id,
    ), session_id = self.session_id )

    assert u"already" in result[ u"error" ]

  def test_redeem_invite_already_redeemed( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )

    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )

    self.login2()
    
    self.http_post( "/users/redeem_invite", dict(
      invite_id = invite_id,
    ), session_id = self.session_id )

    result = self.http_post( "/users/redeem_invite", dict(
      invite_id = invite_id,
    ) )

    assert result[ u"error" ]
    assert u"already" in result[ u"error" ]

  def test_convert_invite_to_access( self ):
    # start the invitee out with access to one notebook
    self.database.execute( self.user2.sql_save_notebook( self.notebooks[ 1 ].object_id, read_write = True, owner = False, rank = 7 ), commit = False )
    self.database.commit()

    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    
    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )
    
    # convert the invite to access for a different user
    invite = self.database.load( Invite, invite_id )
    cherrypy.root.users.convert_invite_to_access( invite, self.user2.object_id )

    access = self.database.select_one( bool, self.user2.sql_has_access(
      invite.notebook_id,
      invite.read_write,
      invite.owner,
    ) )
    assert access is True

    notebook = self.database.load( Notebook, invite.notebook_id )
    access = self.database.select_one( bool, self.user2.sql_has_access(
      notebook.trash_id,
      invite.read_write,
      invite.owner,
    ) )
    assert access is True

    notebooks = self.database.select_many( Notebook, self.user2.sql_load_notebooks() )
    new_notebook = [ notebook for notebook in notebooks if notebook.object_id == invite.notebook_id ][ 0 ]
    assert new_notebook.rank == 8 # one higher than the other notebook this user has access to

    assert invite.redeemed_user_id == self.user2.object_id

  def test_convert_invite_to_access_same_user( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    
    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )
    
    # here, the same user that sent the invite is trying to convert it to access
    invite = self.database.load( Invite, invite_id )
    cherrypy.root.users.convert_invite_to_access( invite, self.user.object_id )

    # assert that the user retains the access they already had
    access = self.database.select_one( bool, self.user.sql_has_access(
      invite.notebook_id,
      invite.read_write,
      invite.owner,
    ) )
    assert access is True

    notebook = self.database.load( Notebook, invite.notebook_id )
    access = self.database.select_one( bool, self.user.sql_has_access(
      notebook.trash_id,
      invite.read_write,
      invite.owner,
    ) )
    assert access is True

    # assert that the invite was not actually redeemed
    assert invite.redeemed_user_id == None

  def test_convert_invite_to_access_twice( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    
    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )
    
    invite = self.database.load( Invite, invite_id )
    cherrypy.root.users.convert_invite_to_access( invite, self.user2.object_id )
    cherrypy.root.users.convert_invite_to_access( invite, self.user2.object_id )

    access = self.database.select_one( bool, self.user2.sql_has_access(
      invite.notebook_id,
      invite.read_write,
      invite.owner,
    ) )
    assert access is True

    notebook = self.database.load( Notebook, invite.notebook_id )
    access = self.database.select_one( bool, self.user2.sql_has_access(
      notebook.trash_id,
      invite.read_write,
      invite.owner,
    ) )
    assert access is True

    assert invite.redeemed_user_id == self.user2.object_id

  @raises( Invite_error )
  def test_convert_invite_with_unknown_user( self ):
    self.login()

    self.user.rate_plan = 1
    self.database.save( self.user )

    email_addresses_list = [ u"foo@example.com" ]
    email_addresses = email_addresses_list[ 0 ]

    self.http_post( "/users/send_invites", dict(
      notebook_id = self.notebooks[ 0 ].object_id,
      email_addresses = email_addresses,
      access = u"viewer",
      invite_button = u"send invites",
    ), session_id = self.session_id )
    
    matches = self.INVITE_LINK_PATTERN.search( smtplib.SMTP.message )
    invite_id = matches.group( 2 )
    
    invite = self.database.load( Invite, invite_id )
    cherrypy.root.users.convert_invite_to_access( invite, u"unknown_user_id" )

  PAYMENT_DATA = {
    u"last_name": u"User",
    u"txn_id": u"txn",
    u"receiver_email": u"unittest@luminotes.com",
    u"payment_status": u"Completed",
    u"payment_gross": u"9.00",
    u"residence_country": u"US",
    u"payer_status": u"verified",
    u"txn_type": u"subscr_payment",
    u"payment_date": u"15:38:18 Jan 10 2008 PST",
    u"first_name": u"Test",
    u"item_name": u"Luminotes extra super",
    u"charset": u"windows-1252",
    u"notify_version": u"2.4",
    u"item_number": u"1",
    u"receiver_id": u"rcv",
    u"business": u"unittest@luminotes.com",
    u"payer_id": u"pyr",
    u"verify_sign": u"vfy",
    u"subscr_id": u"sub",
    u"payment_fee": u"0.56",
    u"mc_fee": u"0.56",
    u"mc_currency": u"USD",
    u"payer_email": u"buyer@luminotes.com",
    u"payment_type": u"instant",
    u"mc_gross": u"9.00",
  }

  def test_paypal_notify_payment( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )
    assert Stub_urllib2.result == u"VERIFIED"
    assert Stub_urllib2.headers.get( u"Content-type" ) == u"application/x-www-form-urlencoded"
    assert Stub_urllib2.url.startswith( "https://" )
    assert u"paypal.com" in Stub_urllib2.url
    assert Stub_urllib2.encoded_params

    # being notified of a mere payment should not change the user's rate plan
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

  def test_paypal_notify_payment_yearly( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"payment_gross" ] = u"90.00"
    data[ u"mc_gross" ] = u"90.00"
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )
    assert Stub_urllib2.result == u"VERIFIED"
    assert Stub_urllib2.headers.get( u"Content-type" ) == u"application/x-www-form-urlencoded"
    assert Stub_urllib2.url.startswith( "https://" )
    assert u"paypal.com" in Stub_urllib2.url
    assert Stub_urllib2.encoded_params

    # being notified of a mere payment should not change the user's rate plan
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

  def test_paypal_notify_payment_invalid( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    Stub_urllib2.result = u"INVALID"
    try:
      result = self.http_post( "/users/paypal_notify", data );
    finally:
      Stub_urllib2.result = u"VERIFIED"

    assert result.get( u"error" )

  def test_paypal_notify_payment_not_complete( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"payment_status" ] = u"NotEvenRemotelyCompleted"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_payment_incorrect_receiver_email( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"receiver_email" ] = u"someoneelse@luminotes.com"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_payment_incorrect_currency( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_currency" ] = u"EUR"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_payment_invalid_item_number( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"item_number" ] = u"2"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_payment_missing_item_number( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )

  def test_paypal_notify_payment_blank_item_number( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"item_number" ] = u""
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )

  def test_paypal_notify_payment_incorrect_gross( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_gross" ] = u"8.75"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_payment_incorrect_amount( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_amount3" ] = u"1.99"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_payment_incorrect_item_name( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"item_name" ] = u"super professional"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_payment_invalid_period1( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"period1" ] = u"5 Y"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_payment_invalid_period1( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"period2" ] = u"7 M"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_payment_invalid_period3( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"period3" ] = u"2 M"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_payment_missing_custom( self ):
    data = dict( self.PAYMENT_DATA )
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_payment_invalid_custom( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = u"(&^(*&"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_payment_unknown_custom( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"custom" ] = u"1337"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_failed( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"txn_type" ] = u"subscr_failed"
    data[ u"custom" ] = self.user.object_id
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )
    assert Stub_urllib2.result == u"VERIFIED"
    assert Stub_urllib2.headers.get( u"Content-type" ) == u"application/x-www-form-urlencoded"
    assert Stub_urllib2.url.startswith( "https://" )
    assert u"paypal.com" in Stub_urllib2.url
    assert Stub_urllib2.encoded_params

    # being notified of a mere failure should not change the user's rate plan
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

  def test_paypal_notify_failed_invalid( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"txn_type" ] = u"subscr_failed"
    data[ u"custom" ] = self.user.object_id
    Stub_urllib2.result = u"INVALID"
    try:
      result = self.http_post( "/users/paypal_notify", data );
    finally:
      Stub_urllib2.result = u"VERIFIED"

    assert result.get( u"error" )

  def test_paypal_notify_failed_incorrect_receiver_email( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"txn_type" ] = u"subscr_failed"
    data[ u"custom" ] = self.user.object_id
    data[ u"receiver_email" ] = u"someoneelse@luminotes.com"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_failed_incorrect_currency( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"txn_type" ] = u"subscr_failed"
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_currency" ] = u"EUR"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_failed_invalid_item_number( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"txn_type" ] = u"subscr_failed"
    data[ u"custom" ] = self.user.object_id
    data[ u"item_number" ] = u"2"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_failed_incorrect_gross( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"txn_type" ] = u"subscr_failed"
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_gross" ] = u"8.75"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_failed_incorrect_amount( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"txn_type" ] = u"subscr_failed"
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_amount3" ] = u"1.99"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_failed_incorrect_item_name( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"txn_type" ] = u"subscr_failed"
    data[ u"custom" ] = self.user.object_id
    data[ u"item_name" ] = u"super professional"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_failed_invalid_period1( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"txn_type" ] = u"subscr_failed"
    data[ u"custom" ] = self.user.object_id
    data[ u"period1" ] = u"5 Y"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_failed_invalid_period1( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"txn_type" ] = u"subscr_failed"
    data[ u"custom" ] = self.user.object_id
    data[ u"period2" ] = u"7 M"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_failed_invalid_period3( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"txn_type" ] = u"subscr_failed"
    data[ u"custom" ] = self.user.object_id
    data[ u"period3" ] = u"2 M"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_failed_missing_custom( self ):
    data = dict( self.PAYMENT_DATA )
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_failed_invalid_custom( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"txn_type" ] = u"subscr_failed"
    data[ u"custom" ] = u"(&^(*&"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  def test_paypal_notify_failed_unknown_custom( self ):
    data = dict( self.PAYMENT_DATA )
    data[ u"txn_type" ] = u"subscr_failed"
    data[ u"custom" ] = u"1337"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )

  SUBSCRIPTION_DATA = {
    u"last_name": u"User",
    u"receiver_email": u"unittest@luminotes.com",
    u"residence_country": u"US",
    u"payer_status": u"verified",
    u"txn_type": u"subscr_signup",
    u"first_name": u"Test",
    u"item_name": u"Luminotes extra super",
    u"charset": u"windows-1252",
    u"notify_version": u"2.4",
    u"recurring": u"1",
    u"item_number": u"1",
    u"payer_id": u"pyr",
    u"period3": u"1 M",
    u"verify_sign": u"vfy",
    u"subscr_id": u"sub",
    u"amount3": u"9.00",
    u"mc_amount3": u"9.00",
    u"mc_currency": u"USD",
    u"subscr_date": u"15:38:16 Jan 10 2008 PST",
    u"payer_email": u"buyer@luminotes.com",
    u"reattempt": u"1",
  }

  def test_paypal_notify_signup( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )
    assert Stub_urllib2.result == u"VERIFIED"
    assert Stub_urllib2.headers.get( u"Content-type" ) == u"application/x-www-form-urlencoded"
    assert Stub_urllib2.url.startswith( "https://" )
    assert u"paypal.com" in Stub_urllib2.url
    assert Stub_urllib2.encoded_params

    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def __load_admin_groups( self ):
    groups = self.database.select_many( Group, self.user.sql_load_groups() )

    return [ group for group in groups if group.admin ]

  def __assert_has_admin_group( self, exactly_one = False ):
    groups = self.__load_admin_groups()

    assert len( groups ) > 0
    if exactly_one is True:
      assert len( groups ) == 1

    assert groups[ 0 ]
    assert groups[ 0 ].name == u"my group"
    assert groups[ 0 ].admin is True

  def __assert_no_admin_group( self ):
    groups = self.__load_admin_groups()

    assert len( groups ) == 0

  def test_paypal_notify_signup_yearly( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"amount3" ] = u"90.00"
    data[ u"mc_amount3" ] = u"90.00"
    data[ u"period3" ] = u"1 Y"
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )
    assert Stub_urllib2.result == u"VERIFIED"
    assert Stub_urllib2.headers.get( u"Content-type" ) == u"application/x-www-form-urlencoded"
    assert Stub_urllib2.url.startswith( "https://" )
    assert u"paypal.com" in Stub_urllib2.url
    assert Stub_urllib2.encoded_params

    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_signup_with_existing_admin_group( self ):
    self.user2.rate_plan = 0
    self.database.save( self.user2, commit = False )

    self.__create_admin_group( add_non_admin_user = True )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )
    assert Stub_urllib2.result == u"VERIFIED"
    assert Stub_urllib2.headers.get( u"Content-type" ) == u"application/x-www-form-urlencoded"
    assert Stub_urllib2.url.startswith( "https://" )
    assert u"paypal.com" in Stub_urllib2.url
    assert Stub_urllib2.encoded_params

    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    # assert that the rate plan of the other user in the group changed as well
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.rate_plan == 1

    # assert that a second admin group wasn't created
    self.__assert_has_admin_group( exactly_one = True )

  def test_paypal_notify_signup_invalid( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    Stub_urllib2.result = u"INVALID"
    try:
      result = self.http_post( "/users/paypal_notify", data );
    finally:
      Stub_urllib2.result = u"VERIFIED"

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_incorrect_receiver_email( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"receiver_email" ] = u"someoneelse@luminotes.com"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_incorrect_currency( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_currency" ] = u"EUR"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_invalid_item_number( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"item_number" ] = u"2"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_incorrect_gross( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_gross" ] = u"8.75"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_incorrect_amount( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_amount3" ] = u"1.99"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_incorrect_item_name( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"item_name" ] = u"super professional"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_invalid_period1( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"period1" ] = u"5 Y"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_invalid_period1( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"period2" ] = u"7 M"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_invalid_period3( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"period3" ] = u"2 M"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_yearly_period3_with_monthly_amount( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"period3" ] = u"1 Y"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_yearly_amount_with_monthly_period3( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_amount3" ] = u"19.90"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_missing_custom( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_invalid_custom( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = u"(&^(*&"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_unknown_custom( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"custom" ] = u"1337"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_missing_recurring( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    del( data[ u"recurring" ] )
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_signup_invalid_recurring( self ):
    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"recurring" ] = u"0"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_modify( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = self.user.object_id
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )
    assert Stub_urllib2.result == u"VERIFIED"
    assert Stub_urllib2.headers.get( u"Content-type" ) == u"application/x-www-form-urlencoded"
    assert Stub_urllib2.url.startswith( "https://" )
    assert u"paypal.com" in Stub_urllib2.url
    assert Stub_urllib2.encoded_params

    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_modify_yearly( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = self.user.object_id
    data[ u"amount3" ] = u"90.00"
    data[ u"mc_amount3" ] = u"90.00"
    data[ u"period3" ] = u"1 Y"
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )
    assert Stub_urllib2.result == u"VERIFIED"
    assert Stub_urllib2.headers.get( u"Content-type" ) == u"application/x-www-form-urlencoded"
    assert Stub_urllib2.url.startswith( "https://" )
    assert u"paypal.com" in Stub_urllib2.url
    assert Stub_urllib2.encoded_params

    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_modify_with_existing_admin_group( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )
    self.user2.rate_plan = 0
    self.database.save( self.user2, commit = False )

    self.__create_admin_group( add_non_admin_user = True )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = self.user.object_id
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )
    assert Stub_urllib2.result == u"VERIFIED"
    assert Stub_urllib2.headers.get( u"Content-type" ) == u"application/x-www-form-urlencoded"
    assert Stub_urllib2.url.startswith( "https://" )
    assert u"paypal.com" in Stub_urllib2.url
    assert Stub_urllib2.encoded_params

    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    # assert that the rate plan of the other user in the group changed as well
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.rate_plan == 1

    # assert that a second admin group wasn't created
    self.__assert_has_admin_group( exactly_one = True )

  def test_paypal_notify_modify_invalid( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = self.user.object_id
    Stub_urllib2.result = u"INVALID"
    try:
      result = self.http_post( "/users/paypal_notify", data );
    finally:
      Stub_urllib2.result = u"VERIFIED"

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_modify_incorrect_receiver_email( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = self.user.object_id
    data[ u"receiver_email" ] = u"someoneelse@luminotes.com"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_modify_incorrect_currency( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_currency" ] = u"EUR"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_modify_invalid_item_number( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = self.user.object_id
    data[ u"item_number" ] = u"2"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_modify_incorrect_gross( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_gross" ] = u"8.75"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_modify_incorrect_amount( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_amount3" ] = u"1.99"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_modify_incorrect_item_name( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = self.user.object_id
    data[ u"item_name" ] = u"super professional"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_modify_invalid_period1( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = self.user.object_id
    data[ u"period1" ] = u"5 Y"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_modify_invalid_period1( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = self.user.object_id
    data[ u"period2" ] = u"7 M"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_modify_invalid_period3( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = self.user.object_id
    data[ u"period3" ] = u"2 M"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_modify_missing_custom( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_modify_invalid_custom( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = u"(&^(*&"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_modify_unknown_custom( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"custom" ] = u"1337"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_modify_missing_recurring( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    del( data[ u"recurring" ] )
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_modify_invalid_recurring( self ):
    self.user.rate_plan = 2
    user = self.database.save( self.user )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_modify"
    data[ u"recurring" ] = u"0"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 2

    self.__assert_no_admin_group()

  def test_paypal_notify_cancel( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = self.user.object_id
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )
    assert Stub_urllib2.result == u"VERIFIED"
    assert Stub_urllib2.headers.get( u"Content-type" ) == u"application/x-www-form-urlencoded"
    assert Stub_urllib2.url.startswith( "https://" )
    assert u"paypal.com" in Stub_urllib2.url
    assert Stub_urllib2.encoded_params

    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def __create_admin_group( self, add_non_admin_user = False ):
    group_id = self.database.next_id( Group, commit = False )
    group = Group.create( group_id, name = u"my group", admin = True )
    self.database.save( group, commit = False )
    self.database.execute( self.user.sql_save_group( group_id, admin = True ) )

    if add_non_admin_user is True:
      self.database.execute( self.user2.sql_save_group( group_id, admin = False ) )

    self.database.commit()

  def test_paypal_notify_cancel_yearly( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = self.user.object_id
    data[ u"amount3" ] = u"90.00"
    data[ u"mc_amount3" ] = u"90.00"
    data[ u"period3" ] = u"1 Y"
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )
    assert Stub_urllib2.result == u"VERIFIED"
    assert Stub_urllib2.headers.get( u"Content-type" ) == u"application/x-www-form-urlencoded"
    assert Stub_urllib2.url.startswith( "https://" )
    assert u"paypal.com" in Stub_urllib2.url
    assert Stub_urllib2.encoded_params

    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_cancel_with_other_user_in_group( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group( add_non_admin_user = True )

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = self.user.object_id
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )
    assert Stub_urllib2.result == u"VERIFIED"
    assert Stub_urllib2.headers.get( u"Content-type" ) == u"application/x-www-form-urlencoded"
    assert Stub_urllib2.url.startswith( "https://" )
    assert u"paypal.com" in Stub_urllib2.url
    assert Stub_urllib2.encoded_params

    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 0

    # assert that the rate plan of the other user in the group changed as well
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.rate_plan == 0

    self.__assert_no_admin_group()

  def test_paypal_notify_cancel_invalid( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = self.user.object_id
    Stub_urllib2.result = u"INVALID"
    try:
      result = self.http_post( "/users/paypal_notify", data );
    finally:
      Stub_urllib2.result = u"VERIFIED"

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_cancel_incorrect_receiver_email( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = self.user.object_id
    data[ u"receiver_email" ] = u"someoneelse@luminotes.com"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_cancel_incorrect_currency( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_currency" ] = u"EUR"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_cancel_invalid_item_number( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = self.user.object_id
    data[ u"item_number" ] = u"2"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_cancel_incorrect_gross( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_gross" ] = u"8.75"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_cancel_incorrect_amount( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = self.user.object_id
    data[ u"mc_amount3" ] = u"1.99"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_cancel_incorrect_item_name( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = self.user.object_id
    data[ u"item_name" ] = u"super professional"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_cancel_invalid_period1( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = self.user.object_id
    data[ u"period1" ] = u"5 Y"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_cancel_invalid_period1( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = self.user.object_id
    data[ u"period2" ] = u"7 M"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_cancel_invalid_period3( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = self.user.object_id
    data[ u"period3" ] = u"2 M"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_cancel_missing_custom( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_cancel_invalid_custom( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = u"(&^(*&"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_cancel_unknown_custom( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"custom" ] = u"1337"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_cancel_missing_recurring( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    del( data[ u"recurring" ] )
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  def test_paypal_notify_cancel_invalid_recurring( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )
    self.__create_admin_group()

    data = dict( self.SUBSCRIPTION_DATA )
    data[ u"txn_type" ] = u"subscr_cancel"
    data[ u"recurring" ] = u"0"
    result = self.http_post( "/users/paypal_notify", data );

    assert result.get( u"error" )
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

    self.__assert_has_admin_group()

  REFUND_DATA = {
    u"last_name": u"User",
    u"txn_id": u"txn",
    u"receiver_email": u"unittest@luminotes.com",
    u"payment_status": u"Refunded",
    u"payment_gross": u"-5.00",
    u"reason_code": u"refund",
    u"residence_country": u"US",
    u"payment_date": u"20:31:40 Jan 11 2008 PST",
    u"first_name": u"Test",
    u"charset": u"windows-1252",
    u"parent_txn_id": u"parent_txn",
    u"notify_version": u"2.4",
    u"item_number": u"1",
    u"receiver_id": u"rcv",
    u"business": u"unittest@luminotes.com",
    u"payer_id": u"pyr",
    u"verify_sign": u"vfy",
    u"subscr_id": u"sub",
    u"payment_fee": u"-0.45",
    u"mc_fee": u"-0.45",
    u"mc_currency": u"USD",
    u"payer_email": u"buyer@luminotes.com",
    u"payment_type": u"instant",
    u"mc_gross": u"-5.00",
  }

  def test_paypal_notify_refund( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )

    data = dict( self.REFUND_DATA )
    data[ u"custom" ] = self.user.object_id
    result = self.http_post( "/users/paypal_notify", data );

    assert len( result ) == 1
    assert result.get( u"session_id" )

    # being notified of a mere refund should not change the user's rate plan
    user = self.database.load( User, self.user.object_id )
    assert user.rate_plan == 1

  DOWNLOAD_PAYMENT_DATA = {
    u"last_name": u"User",
    u"txn_id": u"txn",
    u"receiver_email": u"unittest@luminotes.com",
    u"payment_status": u"Completed",
    u"payment_gross": u"30.00",
    u"residence_country": u"US",
    u"payer_status": u"verified",
    u"txn_type": u"web_accept",
    u"payment_date": u"15:38:18 Jan 10 2008 PST",
    u"first_name": u"Test",
    u"item_name": u"local desktop extravaganza",
    u"charset": u"windows-1252",
    u"notify_version": u"2.4",
    u"item_number": u"5000",
    u"receiver_id": u"rcv",
    u"business": u"unittest@luminotes.com",
    u"payer_id": u"pyr",
    u"verify_sign": u"vfy",
    u"payment_fee": u"1.19",
    u"mc_fee": u"1.19",
    u"mc_currency": u"USD",
    u"shipping": u"0.00",
    u"payer_email": u"buyer@luminotes.com",
    u"payment_type": u"instant",
    u"mc_gross": u"30.00",
    u"quantity": u"1",
  }

  def __assert_download_payment_success( self, result, expect_email = True ):
    assert len( result ) == 1
    assert result.get( u"session_id" )
    assert Stub_urllib2.result == u"VERIFIED"
    assert Stub_urllib2.headers.get( u"Content-type" ) == u"application/x-www-form-urlencoded"
    assert Stub_urllib2.url.startswith( "https://" )
    assert u"paypal.com" in Stub_urllib2.url
    assert Stub_urllib2.encoded_params

    # verify that the user has been granted download access
    download_access = self.database.select_one( Download_access, "select * from download_access order by revision desc limit 1;" );
    assert download_access
    assert download_access.item_number == u"5000"
    assert download_access.transaction_id == u"txn"

    if not expect_email:
      return

    # verify that an email has been sent to the user
    assert smtplib.SMTP.connected == False
    assert "<%s>" % self.settings[ u"global" ][ u"luminotes.support_email" ] in smtplib.SMTP.from_address
    assert smtplib.SMTP.to_addresses == [ u"buyer@luminotes.com" ]
    assert u"Thank you" in smtplib.SMTP.message
    assert u"download" in smtplib.SMTP.message
    assert u"upgrade" in smtplib.SMTP.message

    expected_download_link = u"%s/d/%s" % \
      ( self.settings[ u"global" ][ u"luminotes.https_url" ], download_access.object_id )
    assert expected_download_link in smtplib.SMTP.message

  def test_paypal_notify_download_payment( self ):
    data = dict( self.DOWNLOAD_PAYMENT_DATA )
    result = self.http_post( "/users/paypal_notify", data );
    self.__assert_download_payment_success( result )

  def test_paypal_notify_download_payment_multiple_quantity( self ):
    data = dict( self.DOWNLOAD_PAYMENT_DATA )
    data[ u"mc_gross" ] = u"90.0"
    data[ u"quantity" ] = u"3"
    result = self.http_post( "/users/paypal_notify", data );
    self.__assert_download_payment_success( result )

  def __assert_download_payment_error( self, result ):
    assert u"error" in result
    download_access = self.database.select_one( Download_access, "select * from download_access order by revision desc limit 1;" );
    assert not download_access
    assert not smtplib.SMTP.message

  def test_paypal_notify_download_payment_missing_mc_gross( self ):
    data = dict( self.DOWNLOAD_PAYMENT_DATA )
    del( data[ u"mc_gross" ] )
    result = self.http_post( "/users/paypal_notify", data );
    self.__assert_download_payment_error( result )

  def test_paypal_notify_download_payment_none_mc_gross( self ):
    data = dict( self.DOWNLOAD_PAYMENT_DATA )
    data[ u"mc_gross" ] = None
    result = self.http_post( "/users/paypal_notify", data );
    self.__assert_download_payment_error( result )

  def test_paypal_notify_download_payment_missing_quantity( self ):
    data = dict( self.DOWNLOAD_PAYMENT_DATA )
    del( data[ u"quantity" ] )
    result = self.http_post( "/users/paypal_notify", data );
    self.__assert_download_payment_error( result )

  def test_paypal_notify_download_payment_none_quantity( self ):
    data = dict( self.DOWNLOAD_PAYMENT_DATA )
    data[ u"quantity" ] = None
    result = self.http_post( "/users/paypal_notify", data );
    self.__assert_download_payment_error( result )

  def test_paypal_notify_download_payment_quantity_mc_gross_mismatch( self ):
    data = dict( self.DOWNLOAD_PAYMENT_DATA )
    data[ u"quantity" ] = u"2"
    result = self.http_post( "/users/paypal_notify", data );
    self.__assert_download_payment_error( result )

  def test_paypal_notify_download_payment_mc_gross_fee_mismatch( self ):
    data = dict( self.DOWNLOAD_PAYMENT_DATA )
    data[ u"quantity" ] = u"2"
    data[ u"mc_gross" ] = u"61.0"
    result = self.http_post( "/users/paypal_notify", data );
    self.__assert_download_payment_error( result )

  def test_paypal_notify_download_payment_invalid_item_name( self ):
    data = dict( self.DOWNLOAD_PAYMENT_DATA )
    data[ u"item_name" ] = u"something unexpected"
    result = self.http_post( "/users/paypal_notify", data );
    self.__assert_download_payment_error( result )

  def test_paypal_notify_download_payment_partial_item_name( self ):
    data = dict( self.DOWNLOAD_PAYMENT_DATA )
    data[ u"item_name" ] = u"ultra LOCAL DESKTOP extravaganza digital download!"
    result = self.http_post( "/users/paypal_notify", data );
    self.__assert_download_payment_success( result )

  def test_paypal_notify_download_payment_invalid_txn_type( self ):
    data = dict( self.DOWNLOAD_PAYMENT_DATA )
    data[ u"txn_type" ] = u"web_wtf"
    result = self.http_post( "/users/paypal_notify", data );
    self.__assert_download_payment_error( result )

  def test_paypal_notify_download_payment_invalid_txn_id( self ):
    data = dict( self.DOWNLOAD_PAYMENT_DATA )
    data[ u"txn_id" ] = u"not even remotely valid"
    result = self.http_post( "/users/paypal_notify", data );
    self.__assert_download_payment_error( result )

  def test_paypal_notify_download_payment_missing_payer_email( self ):
    data = dict( self.DOWNLOAD_PAYMENT_DATA )
    data[ u"payer_email" ] = u""
    result = self.http_post( "/users/paypal_notify", data );
    self.__assert_download_payment_success( result, expect_email = False )

  def test_thanks( self ):
    self.user.rate_plan = 1
    user = self.database.save( self.user )

    self.login()

    result = self.http_post( "/users/thanks", dict(
      item_number = u"1",
    ), session_id = self.session_id )

    assert result[ u"user" ].username == self.user.username
    assert len( result[ u"notebooks" ] ) == 5
    notebook = [ notebook for notebook in result[ u"notebooks" ] if notebook.object_id == self.notebooks[ 0 ].object_id ][ 0 ]
    assert notebook.object_id == self.notebooks[ 0 ].object_id
    assert notebook.name == self.notebooks[ 0 ].name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    assert result[ u"login_url" ] == None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"extra super"
    assert rate_plan[ u"storage_quota_bytes" ] == 31337 * 1000

    assert result[ u"conversion" ] == u"subscribe_1"
    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert result[ u"notes" ][ 0 ].title == u"thank you"
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"Thank you" in result[ u"notes" ][ 0 ].contents
    assert u"Luminotes Extra super" in result[ u"notes" ][ 0 ].contents
    assert u"confirmation" not in result[ u"notes" ][ 0 ].contents

  def test_thanks_not_yet_upgraded( self ):
    self.login()

    result = self.http_post( "/users/thanks", dict(
      item_number = u"1",
    ), session_id = self.session_id )

    assert result[ u"user" ].username == self.user.username
    assert result.get( u"conversion" ) == None
    assert len( result[ u"notebooks" ] ) == 5
    notebook = [ notebook for notebook in result[ u"notebooks" ] if notebook.object_id == self.notebooks[ 0 ].object_id ][ 0 ]
    assert notebook.object_id == self.notebooks[ 0 ].object_id
    assert notebook.name == self.notebooks[ 0 ].name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    assert result[ u"login_url" ] == None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert u"processing" in result[ u"notes" ][ 0 ].title
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"being processed" in result[ u"notes" ][ 0 ].contents
    assert u"retry_count=1" in result[ u"notes" ][ 0 ].contents

  def test_thanks_not_yet_upgraded_with_retry( self ):
    self.login()

    result = self.http_post( "/users/thanks", dict(
      item_number = u"1",
      retry_count = u"5",
    ), session_id = self.session_id )

    assert result[ u"user" ].username == self.user.username
    assert result.get( u"conversion" ) == None
    notebook = [ notebook for notebook in result[ u"notebooks" ] if notebook.object_id == self.notebooks[ 0 ].object_id ][ 0 ]
    assert notebook.object_id == self.notebooks[ 0 ].object_id
    assert notebook.name == self.notebooks[ 0 ].name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    assert result[ u"login_url" ] == None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert u"processing" in result[ u"notes" ][ 0 ].title
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"being processed" in result[ u"notes" ][ 0 ].contents
    assert u"retry_count=6" in result[ u"notes" ][ 0 ].contents

  def test_thanks_with_retry_timeout( self ):
    self.login()

    result = self.http_post( "/users/thanks", dict(
      item_number = u"1",
      retry_count = u"16",
    ), session_id = self.session_id )

    assert result[ u"user" ].username == self.user.username
    assert result.get( u"conversion" ) == None
    assert len( result[ u"notebooks" ] ) == 5
    notebook = [ notebook for notebook in result[ u"notebooks" ] if notebook.object_id == self.notebooks[ 0 ].object_id ][ 0 ]
    assert notebook.object_id == self.notebooks[ 0 ].object_id
    assert notebook.name == self.notebooks[ 0 ].name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    assert result[ u"login_url" ] == None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert result[ u"notes" ][ 0 ].title == u"thank you"
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"Thank you" in result[ u"notes" ][ 0 ].contents
    assert u"confirmation" in result[ u"notes" ][ 0 ].contents

  def test_thanks_without_item_number( self ):
    self.login()

    result = self.http_post( "/users/thanks", dict(
    ), session_id = self.session_id )

    assert result[ u"user" ].username == self.user.username
    assert result.get( u"conversion" ) == None
    assert len( result[ u"notebooks" ] ) == 5
    notebook = [ notebook for notebook in result[ u"notebooks" ] if notebook.object_id == self.notebooks[ 0 ].object_id ][ 0 ]
    assert notebook.object_id == self.notebooks[ 0 ].object_id
    assert notebook.name == self.notebooks[ 0 ].name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    assert result[ u"login_url" ] == None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert result[ u"notes" ][ 0 ].title == u"thank you"
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"Thank you" in result[ u"notes" ][ 0 ].contents
    assert u"confirmation" in result[ u"notes" ][ 0 ].contents

  def test_thanks_download( self ):
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"txn"

    download_access = Download_access.create( access_id, item_number, transaction_id )
    self.database.save( download_access )

    self.login()

    result = self.http_post( "/users/thanks_download", dict(
      access_id = access_id,
    ), session_id = self.session_id )

    assert result[ u"user" ].username == self.user.username
    assert len( result[ u"notebooks" ] ) == 5
    notebook = [ notebook for notebook in result[ u"notebooks" ] if notebook.object_id == self.notebooks[ 0 ].object_id ][ 0 ]
    assert notebook.object_id == self.notebooks[ 0 ].object_id
    assert notebook.name == self.notebooks[ 0 ].name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    assert result[ u"login_url" ] == None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert result[ u"conversion" ] == u"download_5000"
    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert result[ u"notes" ][ 0 ].title == u"thank you"
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"Thank you" in result[ u"notes" ][ 0 ].contents
    assert u"Luminotes Desktop" in result[ u"notes" ][ 0 ].contents
    assert u"Download" in result[ u"notes" ][ 0 ].contents
    assert VERSION in result[ u"notes" ][ 0 ].contents

    expected_download_link = u"%s/files/download_product?access_id=%s" % \
      ( self.settings[ u"global" ][ u"luminotes.https_url" ], access_id )
    assert expected_download_link in result[ u"notes" ][ 0 ].contents

  def test_thanks_download_without_login( self ):
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"txn"

    download_access = Download_access.create( access_id, item_number, transaction_id )
    self.database.save( download_access )

    result = self.http_post( "/users/thanks_download", dict(
      access_id = access_id,
    ) )

    assert result[ u"user" ].username == self.anonymous.username
    assert len( result[ u"notebooks" ] ) == 1

    assert result[ u"login_url" ]
    assert result[ u"logout_url" ]

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert result[ u"conversion" ] == u"download_5000"
    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert result[ u"notes" ][ 0 ].title == u"thank you"
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"Thank you" in result[ u"notes" ][ 0 ].contents
    assert u"Luminotes Desktop" in result[ u"notes" ][ 0 ].contents
    assert u"Download" in result[ u"notes" ][ 0 ].contents
    assert VERSION in result[ u"notes" ][ 0 ].contents

    expected_download_link = u"%s/files/download_product?access_id=%s" % \
      ( self.settings[ u"global" ][ u"luminotes.https_url" ], access_id )
    assert expected_download_link in result[ u"notes" ][ 0 ].contents

  def test_thanks_download_tx( self ):
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"txn"

    download_access = Download_access.create( access_id, item_number, transaction_id )
    self.database.save( download_access )

    self.login()

    result = self.http_post( "/users/thanks_download", dict(
      tx = transaction_id,
    ), session_id = self.session_id )

    redirect = result.get( u"redirect" )
    expected_redirect = "/users/thanks_download?access_id=%s" % access_id
    assert redirect == expected_redirect

  def test_thanks_download_invalid_tx( self ):
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"invalid txn id"

    download_access = Download_access.create( access_id, item_number, transaction_id )
    self.database.save( download_access )

    self.login()

    result = self.http_post( "/users/thanks_download", dict(
      tx = transaction_id,
    ), session_id = self.session_id )

    assert u"error" in result

  def test_thanks_download_not_yet_paid( self ):
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"txn"

    self.login()

    result = self.http_post( "/users/thanks_download", dict(
      access_id = access_id,
    ), session_id = self.session_id )

    # an unknown transaction id might just mean we're still waiting for the transaction to come in,
    # so expect a retry
    assert result[ u"user" ].username == self.user.username
    assert len( result[ u"notebooks" ] ) == 5
    notebook = [ notebook for notebook in result[ u"notebooks" ] if notebook.object_id == self.notebooks[ 0 ].object_id ][ 0 ]
    assert notebook.object_id == self.notebooks[ 0 ].object_id
    assert notebook.name == self.notebooks[ 0 ].name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    assert result[ u"login_url" ] == None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert not result.get( u"conversion" )
    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert u"processing" in result[ u"notes" ][ 0 ].title
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"being processed" in result[ u"notes" ][ 0 ].contents
    assert u"retry_count=1" in result[ u"notes" ][ 0 ].contents

  def test_thanks_download_not_yet_paid_with_retry( self ):
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"txn"

    self.login()

    result = self.http_post( "/users/thanks_download", dict(
      access_id = access_id,
      retry_count = u"3",
    ), session_id = self.session_id )

    # an unknown transaction id might just mean we're still waiting for the transaction to come in,
    # so expect a retry
    assert result[ u"user" ].username == self.user.username
    assert len( result[ u"notebooks" ] ) == 5
    notebook = [ notebook for notebook in result[ u"notebooks" ] if notebook.object_id == self.notebooks[ 0 ].object_id ][ 0 ]
    assert notebook.object_id == self.notebooks[ 0 ].object_id
    assert notebook.name == self.notebooks[ 0 ].name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    assert result[ u"login_url" ] == None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert not result.get( u"conversion" )
    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert u"processing" in result[ u"notes" ][ 0 ].title
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"being processed" in result[ u"notes" ][ 0 ].contents
    assert u"retry_count=4" in result[ u"notes" ][ 0 ].contents

  def test_thanks_download_not_yet_paid_with_retry_timeout( self ):
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"txn"

    self.login()

    result = self.http_post( "/users/thanks_download", dict(
      access_id = access_id,
      retry_count = u"16",
    ), session_id = self.session_id )

    # an unknown transaction id might just mean we're still waiting for the transaction to come in,
    # so expect a retry
    assert result[ u"user" ].username == self.user.username
    assert len( result[ u"notebooks" ] ) == 5
    notebook = [ notebook for notebook in result[ u"notebooks" ] if notebook.object_id == self.notebooks[ 0 ].object_id ][ 0 ]
    assert notebook.object_id == self.notebooks[ 0 ].object_id
    assert notebook.name == self.notebooks[ 0 ].name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    assert result[ u"login_url" ] == None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert not result.get( u"conversion" )
    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert result[ u"notes" ][ 0 ].title == u"thank you"
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"Thank you" in result[ u"notes" ][ 0 ].contents
    assert u"confirmation" in result[ u"notes" ][ 0 ].contents

  def test_thanks_download_not_yet_paid_tx( self ):
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"txn"

    self.login()

    result = self.http_post( "/users/thanks_download", dict(
      tx = transaction_id,
    ), session_id = self.session_id )

    # an unknown transaction id might just mean we're still waiting for the transaction to come in,
    # so expect a retry
    assert result[ u"user" ].username == self.user.username
    assert len( result[ u"notebooks" ] ) == 5
    notebook = [ notebook for notebook in result[ u"notebooks" ] if notebook.object_id == self.notebooks[ 0 ].object_id ][ 0 ]
    assert notebook.object_id == self.notebooks[ 0 ].object_id
    assert notebook.name == self.notebooks[ 0 ].name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    assert result[ u"login_url" ] == None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert not result.get( u"conversion" )
    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert u"processing" in result[ u"notes" ][ 0 ].title
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"being processed" in result[ u"notes" ][ 0 ].contents
    assert u"retry_count=1" in result[ u"notes" ][ 0 ].contents

  def test_thanks_download_not_yet_paid_tx_with_retry( self ):
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"txn"

    self.login()

    result = self.http_post( "/users/thanks_download", dict(
      tx = transaction_id,
      item_number = item_number,
      retry_count = u"3",
    ), session_id = self.session_id )

    # an unknown transaction id might just mean we're still waiting for the transaction to come in,
    # so expect a retry
    assert result[ u"user" ].username == self.user.username
    assert len( result[ u"notebooks" ] ) == 5
    notebook = [ notebook for notebook in result[ u"notebooks" ] if notebook.object_id == self.notebooks[ 0 ].object_id ][ 0 ]
    assert notebook.object_id == self.notebooks[ 0 ].object_id
    assert notebook.name == self.notebooks[ 0 ].name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    assert result[ u"login_url" ] == None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert not result.get( u"conversion" )
    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert u"processing" in result[ u"notes" ][ 0 ].title
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"being processed" in result[ u"notes" ][ 0 ].contents
    assert u"retry_count=4" in result[ u"notes" ][ 0 ].contents

  def test_thanks_download_not_yet_paid_tx_with_retry_timeout( self ):
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"txn"

    self.login()

    result = self.http_post( "/users/thanks_download", dict(
      tx = transaction_id,
      retry_count = u"16",
    ), session_id = self.session_id )

    # an unknown transaction id might just mean we're still waiting for the transaction to come in,
    # so expect a retry
    assert result[ u"user" ].username == self.user.username
    assert len( result[ u"notebooks" ] ) == 5
    notebook = [ notebook for notebook in result[ u"notebooks" ] if notebook.object_id == self.notebooks[ 0 ].object_id ][ 0 ]
    assert notebook.object_id == self.notebooks[ 0 ].object_id
    assert notebook.name == self.notebooks[ 0 ].name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.rank == 0

    assert result[ u"login_url" ] == None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/users/logout"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337 * 10

    assert not result.get( u"conversion" )
    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert result[ u"notes" ][ 0 ].title == u"thank you"
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"Thank you" in result[ u"notes" ][ 0 ].contents
    assert u"confirmation" in result[ u"notes" ][ 0 ].contents

  def test_thanks_download_missing_tx_missing_access_id( self ):
    self.login()

    result = self.http_post( "/users/thanks_download", dict(
    ), session_id = self.session_id )

    assert u"error" in result

  def test_thanks_download_invalid_access_id( self ):
    access_id = u"invalid access id"
    transaction_id = u"txn"

    self.login()

    result = self.http_post( "/users/thanks_download", dict(
      access_id = access_id,
    ), session_id = self.session_id )

    assert u"error" in result

  def test_rate_plan( self ):
    plan_index = 1
    rate_plan = cherrypy.root.users.rate_plan( plan_index )

    assert rate_plan
    assert rate_plan == self.settings[ u"global" ][ u"luminotes.rate_plans" ][ plan_index ]

  def test_update_settings( self ):
    self.login()
    previous_revision = self.user.revision

    result = self.http_post( "/users/update_settings", dict(
      email_address = self.new_email_address,
      settings_button = u"save settings",
    ), session_id = self.session_id )

    assert result[ u"email_address" ] == self.new_email_address

    user = self.database.load( User, self.user.object_id )
    assert user.email_address == self.new_email_address
    assert user.revision > previous_revision

  def test_update_settings_without_login( self ):
    original_revision = self.user.revision

    result = self.http_post( "/users/update_settings", dict(
      email_address = self.new_email_address,
      settings_button = u"save settings",
    ) )

    assert u"access" in result[ u"error" ]

    user = self.database.load( User, self.user.object_id )
    assert user.email_address == self.email_address
    assert user.revision == original_revision

  def test_update_settings_with_same_email_address( self ):
    self.login()
    original_revision = self.user.revision

    result = self.http_post( "/users/update_settings", dict(
      email_address = self.email_address,
      settings_button = u"save settings",
    ), session_id = self.session_id )

    assert result[ u"email_address" ] == self.email_address

    user = self.database.load( User, self.user.object_id )
    assert user.email_address == self.email_address
    assert user.revision == original_revision

  def test_update_settings_with_invalid_email_address( self ):
    original_revision = self.user.revision

    result = self.http_post( "/users/update_settings", dict(
      email_address = u"foo@bar@com",
      settings_button = u"save settings",
    ) )

    assert u"invalid" in result[ u"error" ]

    user = self.database.load( User, self.user.object_id )
    assert user.email_address == self.email_address
    assert user.revision == original_revision

  def test_update_settings_with_blank_email_address( self ):
    self.login()
    previous_revision = self.user.revision

    result = self.http_post( "/users/update_settings", dict(
      email_address = u"",
      settings_button = u"save settings",
    ), session_id = self.session_id )

    assert result[ u"email_address" ] == None

    user = self.database.load( User, self.user.object_id )
    assert user.email_address == None
    assert user.revision > previous_revision

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
