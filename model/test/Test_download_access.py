from model.Download_access import Download_access


class Test_download_access( object ):
  def setUp( self ):
    self.object_id = u"17"
    self.item_number = u"999"
    self.transaction_id = u"foooooooo234"

    self.download_access = Download_access.create( self.object_id, self.item_number, self.transaction_id )

  def test_create( self ):
    assert self.download_access.object_id == self.object_id
    assert self.download_access.item_number == self.item_number
    assert self.download_access.transaction_id == self.transaction_id
