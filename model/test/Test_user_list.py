from model.User import User
from model.User_list import User_list


class Test_user_list( object ):
  def setUp( self ):
    self.object_id = u"17"
    self.secondary_id = u"mylist"

    self.user_list = User_list( self.object_id, self.secondary_id )
    self.user = User( u"18", u"bob", u"pass", u"bob@example.com" )
    self.user2 = User( u"19", u"rob", u"pass2", u"rob@example.com" )

  def test_create( self ):
    assert self.user_list.object_id == self.object_id
    assert self.user_list.secondary_id == self.secondary_id
    assert self.user_list.users == []

  def test_add_user( self ):
    previous_revision = self.user_list.revision
    self.user_list.add_user( self.user )

    assert self.user_list.users == [ self.user ]
    assert self.user_list.revision > previous_revision

  def test_add_user_twice( self ):
    self.user_list.add_user( self.user )
    current_revision = self.user_list.revision
    self.user_list.add_user( self.user )

    assert self.user_list.users == [ self.user ]
    assert self.user_list.revision == current_revision

  def test_add_two_users( self ):
    previous_revision = self.user_list.revision
    self.user_list.add_user( self.user )
    self.user_list.add_user( self.user2 )

    assert self.user_list.users == [ self.user, self.user2 ]
    assert self.user_list.revision > previous_revision

  def test_remove_user( self ):
    self.user_list.add_user( self.user )
    previous_revision = self.user_list.revision
    self.user_list.remove_user( self.user )

    assert self.user_list.users == []
    assert self.user_list.revision > previous_revision

  def test_remove_user_twice( self ):
    self.user_list.add_user( self.user )
    self.user_list.remove_user( self.user )
    current_revision = self.user_list.revision
    self.user_list.remove_user( self.user )

    assert self.user_list.users == []
    assert self.user_list.revision == current_revision
