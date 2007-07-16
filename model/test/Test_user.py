from nose.tools import raises
from model.User import User
from model.Notebook import Notebook


class Test_user( object ):
  def setUp( self ):
    self.object_id = 17
    self.username = u"bob"
    self.password = u"foobar"
    self.email_address = u"bob@example.com"

    self.user = User( self.object_id, self.username, self.password, self.email_address )

  def test_create( self ):
    assert self.user.username == self.username
    assert self.user.email_address == self.email_address
    assert self.user.notebooks == []

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

  def test_set_notebooks( self ):
    previous_revision = self.user.revision
    notebook_id = 33
    notebook = Notebook( notebook_id, u"my notebook" )
    self.user.notebooks = [ notebook ]
    
    assert len( self.user.notebooks ) == 1
    assert self.user.notebooks[ 0 ].object_id == notebook_id
    assert self.user.revision > previous_revision


class Test_user_with_notebooks( object ):
  def setUp( self ):
    self.object_id = 17
    self.username = u"bob"
    self.password = u"foobar"
    self.email_address = u"bob@example.com"
    self.notebooks = [
      Notebook( 33, u"my notebook" ),
      Notebook( 34, u"my other notebook" ),
    ]

    self.user = User( self.object_id, self.username, self.password, self.email_address, self.notebooks )

  def test_create( self ):
    assert self.user.username == self.username
    assert self.user.email_address == self.email_address
    assert self.user.notebooks == self.notebooks

  def test_set_existing_notebooks( self ):
    previous_revision = self.user.revision
    self.user.notebooks = [ self.notebooks[ 1 ] ]
    
    assert len( self.user.notebooks ) == 1
    assert self.user.notebooks[ 0 ].object_id == self.notebooks[ 1 ].object_id
    assert self.user.revision > previous_revision

  def test_set_new_notebooks( self ):
    previous_revision = self.user.revision
    notebook_id = 35
    notebook = Notebook( notebook_id, u"my new notebook" )
    self.user.notebooks = [ notebook ]
    
    assert len( self.user.notebooks ) == 1
    assert self.user.notebooks[ 0 ].object_id == notebook_id
    assert self.user.revision > previous_revision

  def test_has_access_true( self ):
    assert self.user.has_access( self.notebooks[ 0 ].object_id ) == True

  def test_has_access_true( self ):
    notebook_id = 35
    notebook = Notebook( notebook_id, u"my new notebook" )
    assert self.user.has_access( notebook.object_id ) == False
