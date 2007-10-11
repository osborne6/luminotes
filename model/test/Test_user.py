from pytz import utc
from datetime import datetime, timedelta
from model.User import User


class Test_user( object ):
  def setUp( self ):
    self.object_id = u"17"
    self.username = u"bob"
    self.password = u"foobar"
    self.email_address = u"bob@example.com"
    self.delta = timedelta( seconds = 1 )

    self.user = User.create( self.object_id, self.username, self.password, self.email_address )

  def test_create( self ):
    assert self.user.object_id == self.object_id
    assert datetime.now( tz = utc ) - self.user.revision < self.delta
    assert self.user.username == self.username
    assert self.user.email_address == self.email_address
    assert self.user.storage_bytes == 0
    assert self.user.rate_plan == 0

  def test_check_correct_password( self ):
    assert self.user.check_password( self.password ) == True

  def test_check_incorrect_password( self ):
    assert self.user.check_password( u"wrong" ) == False

  def test_set_password( self ):
    previous_revision = self.user.revision
    new_password = u"newpass"
    self.user.password = new_password

    assert self.user.check_password( self.password ) == False
    assert self.user.check_password( new_password ) == True
    assert self.user.revision > previous_revision

  def test_set_none_password( self ):
    previous_revision = self.user.revision
    new_password = None
    self.user.password = new_password

    assert self.user.check_password( self.password ) == False
    assert self.user.check_password( new_password ) == False
    assert self.user.revision > previous_revision

  def test_set_storage_bytes( self ):
    previous_revision = self.user.revision
    storage_bytes = 44
    self.user.storage_bytes = storage_bytes
    
    assert self.user.storage_bytes == storage_bytes
    assert self.user.revision > previous_revision

  def test_set_rate_plan( self ):
    previous_revision = self.user.revision
    rate_plan = 2
    self.user.rate_plan = rate_plan
    
    assert self.user.rate_plan == rate_plan
    assert self.user.revision > previous_revision

  def test_to_dict( self ):
    d = self.user.to_dict()

    assert d.get( "username" ) == self.username
    assert d.get( "storage_bytes" ) == self.user.storage_bytes
    assert d.get( "rate_plan" ) == self.user.rate_plan
