from datetime import datetime
from model.User_revision import User_revision


class Test_user_revision( object ):
  def setUp( self ):
    self.revision = datetime.now()
    self.user_id = u"77"
    self.username = u"bob"

    self.user_revision = User_revision( self.revision, self.user_id, self.username )

  def test_create( self ):
    assert self.user_revision.revision == self.revision
    assert self.user_revision.user_id == self.user_id
    assert self.user_revision.username == self.username

  def test_to_dict( self ):
    d = self.user_revision.to_dict()

    assert d.get( "revision" ) == self.revision
    assert d.get( "user_id" ) == self.user_id
    assert d.get( "username" ) == self.username
