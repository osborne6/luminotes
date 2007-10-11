from model.User import User
from model.Password_reset import Password_reset


class Test_password_reset( object ):
  def setUp( self ):
    self.object_id = u"17"
    self.email_address = u"bob@example.com"

    self.password_reset = Password_reset.create( self.object_id, self.email_address )

  def test_create( self ):
    assert self.password_reset.object_id == self.object_id
    assert self.password_reset.email_address == self.email_address
    assert self.password_reset.redeemed == False

  def test_redeem( self ):
    previous_revision = self.password_reset.revision
    self.password_reset.redeemed = True

    assert self.password_reset.redeemed == True
    assert self.password_reset.revision > previous_revision

  def test_redeem_twice( self ):
    self.password_reset.redeemed = True
    current_revision = self.password_reset.revision
    self.password_reset.redeemed = True

    assert self.password_reset.redeemed == True
    assert self.password_reset.revision == current_revision

  def test_unredeem( self ):
    self.password_reset.redeemed = True
    previous_revision = self.password_reset.revision
    self.password_reset.redeemed = False

    assert self.password_reset.redeemed == False
    assert self.password_reset.revision > previous_revision
