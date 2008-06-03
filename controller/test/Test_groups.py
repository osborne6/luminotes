from Test_controller import Test_controller
import Stub_urllib2
from controller.Groups import Groups
from model.Group import Group
from model.User import User


class Test_groups( Test_controller ):
  def setUp( self ):
    Test_controller.setUp( self )
    Groups.urllib2 = Stub_urllib2

    self.group_name = u"my group"
    self.group_name2 = u"other group"
    self.username = u"mulder"
    self.password = u"trustno1"
    self.email_address = u"out-there@example.com"
    self.username2 = u"scully"
    self.password2 = u"trustsome1"
    self.email_address2 = u"out-there@example.com"
    self.username3 = u"skinner"
    self.password3 = u"trustne1"
    self.email_address3 = u"somewhere@gov.gov"

    self.group = Group.create( self.database.next_id( Group ), self.group_name )
    self.database.save( self.group, commit = False )

    self.group2 = Group.create( self.database.next_id( Group ), self.group_name )
    self.database.save( self.group2, commit = False )

    self.user = User.create( self.database.next_id( User ), self.username, self.password, self.email_address )
    self.database.save( self.user, commit = False )
    self.database.execute( self.user.sql_save_group( self.group.object_id, admin = False ) )

    self.user2 = User.create( self.database.next_id( User ), self.username2, self.password2, self.email_address2 )
    self.database.save( self.user2, commit = False )
    self.database.execute( self.user2.sql_save_group( self.group.object_id, admin = True ) )

    self.user3 = User.create( self.database.next_id( User ), self.username3, self.password3, self.email_address3 )
    self.database.save( self.user3, commit = False )
    self.database.execute( self.user3.sql_save_group( self.group.object_id, admin = False ) )

    self.database.commit()

  def test_load_users( self ):
    self.login2()

    result = self.http_post( "/groups/load_users", dict(
      group_id = self.group.object_id,
    ), session_id = self.session_id )

    assert len( result[ u"admin_users" ] ) == 1
    assert result[ u"admin_users" ][ 0 ].object_id == self.user2.object_id
    assert result[ u"admin_users" ][ 0 ].username == self.user2.username

    assert len( result[ u"other_users" ] ) == 2
    assert result[ u"other_users" ][ 0 ].object_id == self.user.object_id
    assert result[ u"other_users" ][ 0 ].username == self.user.username
    assert result[ u"other_users" ][ 1 ].object_id == self.user3.object_id
    assert result[ u"other_users" ][ 1 ].username == self.user3.username

    assert result[ u"group" ].object_id == self.group.object_id
    assert result[ u"group" ].name == self.group.name
    assert result[ u"group" ].admin == self.group.admin

  def test_load_users_without_access( self ):
    self.login2()

    result = self.http_post( "/groups/load_users", dict(
      group_id = self.group2.object_id,
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]

  def test_load_users_without_admin_access( self ):
    self.login()

    result = self.http_post( "/groups/load_users", dict(
      group_id = self.group.object_id,
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]

  def test_load_users_with_unknown_group( self ):
    self.login()

    result = self.http_post( "/groups/load_users", dict(
      group_id = u"unknowngroupid",
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]

  def test_update_settings( self ):
    self.login2()
    new_name = u"new group name"

    result = self.http_post( "/groups/update_settings", dict(
      group_id = self.group.object_id,
      group_name = new_name,
      group_settings_button = u"save settings",
    ), session_id = self.session_id )
    
    assert u"saved" in result[ u"message" ]

    group = self.database.load( Group, self.group.object_id )
    assert group.name == new_name

  def test_update_settings_without_access( self ):
    self.login2()
    new_name = u"new group name"

    result = self.http_post( "/groups/update_settings", dict(
      group_id = self.group2.object_id,
      group_name = new_name,
      group_settings_button = u"save settings",
    ), session_id = self.session_id )
    
    assert u"access" in result[ u"error" ]

    group = self.database.load( Group, self.group.object_id )
    assert group.name == self.group.name

  def test_update_settings_without_admin_access( self ):
    self.login()
    new_name = u"new group name"

    result = self.http_post( "/groups/update_settings", dict(
      group_id = self.group.object_id,
      group_name = new_name,
      group_settings_button = u"save settings",
    ), session_id = self.session_id )
    
    assert u"access" in result[ u"error" ]

    group = self.database.load( Group, self.group.object_id )
    assert group.name == self.group.name

  def test_update_settings_with_unknown_group( self ):
    self.login2()
    new_name = u"new group name"

    result = self.http_post( "/groups/update_settings", dict(
      group_id = u"unknowngroupid",
      group_name = new_name,
      group_settings_button = u"save settings",
    ), session_id = self.session_id )
    
    assert u"access" in result[ u"error" ]

    group = self.database.load( Group, self.group.object_id )
    assert group.name == self.group.name

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
