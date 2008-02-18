from pytz import utc
from datetime import datetime, timedelta
from model.Invite import Invite


class Test_invite( object ):
  def setUp( self ):
    self.object_id = u"17"
    self.from_user_id = u"18"
    self.notebook_id = u"19"
    self.email_address = u"bob@example.com"
    self.read_write = True
    self.owner = False
    self.delta = timedelta( seconds = 1 )

    self.invite = Invite.create( self.object_id, self.from_user_id, self.notebook_id,
                                 self.email_address, self.read_write, self.owner )

  def test_create( self ):
    assert self.invite.object_id == self.object_id
    assert self.invite.from_user_id == self.from_user_id
    assert self.invite.notebook_id == self.notebook_id
    assert self.invite.email_address == self.email_address
    assert self.invite.read_write == self.read_write
    assert self.invite.owner == self.owner
    assert self.invite.redeemed_user_id == None
    assert self.invite.redeemed_username == None

  def test_redeem( self ):
    previous_revision = self.invite.revision
    redeemed_user_id = u"20"
    self.invite.redeemed_user_id = redeemed_user_id

    assert self.invite.redeemed_user_id == redeemed_user_id
    assert self.invite.revision > previous_revision

  def test_redeem_twice( self ):
    redeemed_user_id = u"20"
    self.invite.redeemed_user_id = redeemed_user_id
    current_revision = self.invite.revision
    self.invite.redeemed_user_id = redeemed_user_id

    assert self.invite.redeemed_user_id == redeemed_user_id
    assert self.invite.revision == current_revision

  def test_to_dict( self ):
    d = self.invite.to_dict()

    assert d.get( "object_id" ) == self.object_id
    assert datetime.now( tz = utc ) - d.get( "revision" ) < self.delta
    assert d.get( "from_user_id" ) == self.from_user_id
    assert d.get( "notebook_id" ) == self.notebook_id
    assert d.get( "read_write" ) == self.read_write
    assert d.get( "owner" ) == self.owner
    assert d.get( "redeemed_user_id" ) == None
    assert d.get( "redeemed_username" ) == None
