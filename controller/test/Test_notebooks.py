# -*- coding: utf8 -*-

import re
import csv
import types
import cherrypy
import urllib
from nose.tools import raises
from StringIO import StringIO
from urllib import quote
from Test_controller import Test_controller
from model.Notebook import Notebook
from model.Note import Note
from model.User import User
from model.Invite import Invite
from model.File import File
from controller.Notebooks import Access_error
from controller.Files import Upload_file


class Test_notebooks( Test_controller ):
  def setUp( self ):
    Test_controller.setUp( self )

    self.notebook = None
    self.anon_notebook = None
    self.unknown_notebook_id = "17"
    self.unknown_note_id = "42"
    self.username = u"mulder"
    self.password = u"trustno1"
    self.email_address = u"outthere@example.com"
    self.username2 = u"deepthroat"
    self.password2 = u"mmmtobacco"
    self.email_address2 = u"parkinglot@example.com"
    self.user = None
    self.user2 = None
    self.invite = None
    self.anonymous = None
    self.session_id = None
    self.file_id = "22"
    self.filename = "file.csv"
    self.content_type = "text/csv"

    # make Upload_file deal in fake files rather than actually using the filesystem
    Upload_file.fake_files = {} # map of file_id to fake file object

    @staticmethod
    def open_file( file_id, mode = None ):
      fake_file = Upload_file.fake_files.get( file_id )

      if fake_file:
        return fake_file

      fake_file = StringIO()
      Upload_file.fake_files[ file_id ] = fake_file
      return fake_file

    @staticmethod
    def open_image( file_id ):
      fake_file = Upload_file.fake_files.get( file_id )

      return Image.open( fake_file )

    @staticmethod
    def delete_file( file_id ):
      fake_file = Upload_file.fake_files.get( file_id )

      if fake_file is None:
        raise IOError()

      del( Upload_file.fake_files[ file_id ] )

    @staticmethod
    def exists( file_id ):
      fake_file = Upload_file.fake_files.get( file_id )

      return fake_file is not None

    def close( self ):
      self.complete()

    Upload_file.open_file = open_file
    Upload_file.open_image = open_image
    Upload_file.delete_file = delete_file
    Upload_file.exists = exists
    Upload_file.close = close

    self.make_users()
    self.make_notebooks()
    self.make_invites()
    self.database.commit()

  def make_notebooks( self ):
    user_id = self.user.object_id

    self.trash = Notebook.create( self.database.next_id( Notebook ), u"trash", user_id = user_id )
    self.database.save( self.trash, commit = False )
    self.notebook = Notebook.create( self.database.next_id( Notebook ), u"notebook", self.trash.object_id, user_id = user_id )
    self.database.save( self.notebook, commit = False )

    note_id = self.database.next_id( Note )
    self.note = Note.create( note_id, u"<h3>my title</h3>blah", notebook_id = self.notebook.object_id, startup = True, user_id = user_id )
    self.database.save( self.note, commit = False )

    note_id = self.database.next_id( Note )
    self.note2 = Note.create( note_id, u"<h3>other title</h3>whee", notebook_id = self.notebook.object_id, user_id = user_id )
    self.database.save( self.note2, commit = False )

    self.anon_notebook = Notebook.create( self.database.next_id( Notebook ), u"anon_notebook", user_id = user_id )
    self.database.save( self.anon_notebook, commit = False )

    self.database.execute( self.user.sql_save_notebook( self.notebook.object_id, read_write = True, owner = True, rank = 0 ) )
    self.database.execute( self.user.sql_save_notebook( self.notebook.trash_id, read_write = True, owner = True ) )
    self.database.execute( self.user.sql_save_notebook( self.anon_notebook.object_id, read_write = False, owner = False ) )

    self.database.execute( self.user2.sql_save_notebook( self.notebook.object_id, read_write = True, owner = False, rank = 0 ) )
    self.database.execute( self.user2.sql_save_notebook( self.notebook.trash_id, read_write = True, owner = False ) )

  def make_extra_notebooks( self ):
    user_id = self.user.object_id

    self.trash2 = Notebook.create( self.database.next_id( Notebook ), u"trash", user_id = user_id )
    self.database.save( self.trash2, commit = False )
    self.notebook2 = Notebook.create( self.database.next_id( Notebook ), u"notebook", self.trash2.object_id, user_id = user_id )
    self.database.save( self.notebook2, commit = False )

    self.trash3 = Notebook.create( self.database.next_id( Notebook ), u"trash", user_id = user_id )
    self.database.save( self.trash3, commit = False )
    self.notebook3 = Notebook.create( self.database.next_id( Notebook ), u"notebook", self.trash3.object_id, user_id = user_id )
    self.database.save( self.notebook3, commit = False )

    self.database.execute( self.user.sql_save_notebook( self.notebook2.object_id, read_write = True, owner = True, rank = 1 ) )
    self.database.execute( self.user.sql_save_notebook( self.notebook2.trash_id, read_write = True, owner = True ) )
    self.database.execute( self.user.sql_save_notebook( self.notebook3.object_id, read_write = True, owner = True, rank = 2 ) )
    self.database.execute( self.user.sql_save_notebook( self.notebook3.trash_id, read_write = True, owner = True ) )

    self.database.commit()

  def make_users( self ):
    self.user = User.create( self.database.next_id( User ), self.username, self.password, self.email_address )
    self.database.save( self.user, commit = False )

    self.user2 = User.create( self.database.next_id( User ), self.username2, self.password2, self.email_address2 )
    self.database.save( self.user2, commit = False )

    self.anonymous = User.create( self.database.next_id( User ), u"anonymous" )
    self.database.save( self.anonymous, commit = False )

  def make_invites( self ):
    self.invite = Invite.create(
      self.database.next_id( Invite ), self.user.object_id, self.notebook.object_id,
      u"skinner@example.com", read_write = True, owner = False,
    )
    self.database.save( self.invite, commit = False )

  def test_default_without_login( self ):
    path = "/notebooks/%s" % self.notebook.object_id
    result = self.http_get( path )
    
    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s" % self.notebook.object_id,
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 2 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 2 ].read_write == True
    assert result.get( u"notebooks" )[ 2 ].owner == True
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == True
    assert result.get( u"notebook" ).owner == True
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert len( result.get( "recent_notes" ) ) == 2
    assert result.get( "recent_notes" )[ 0 ].object_id == self.note2.object_id
    assert result.get( "recent_notes" )[ 1 ].object_id == self.note.object_id

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_as_preview_viewer( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?preview=viewer" % self.notebook.object_id,
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 1
    assert result.get( u"notebooks" )[ 0 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 0 ].read_write == False
    assert result.get( u"notebooks" )[ 0 ].owner == False
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == False
    assert result.get( u"notebook" ).owner == False
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert len( result.get( "recent_notes" ) ) == 2
    assert result.get( "recent_notes" )[ 0 ].object_id == self.note2.object_id
    assert result.get( "recent_notes" )[ 1 ].object_id == self.note.object_id

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_as_preview_collaborator( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?preview=collaborator" % self.notebook.object_id,
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 1
    assert result.get( u"notebooks" )[ 0 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 0 ].read_write == True
    assert result.get( u"notebooks" )[ 0 ].owner == False
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == True
    assert result.get( u"notebook" ).owner == False
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert len( result.get( "recent_notes" ) ) == 2
    assert result.get( "recent_notes" )[ 0 ].object_id == self.note2.object_id
    assert result.get( "recent_notes" )[ 1 ].object_id == self.note.object_id

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_as_preview_owner( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?preview=owner" % self.notebook.object_id,
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 2 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 2 ].read_write == True
    assert result.get( u"notebooks" )[ 2 ].owner == True
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == True
    assert result.get( u"notebook" ).owner == True
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert len( result.get( "recent_notes" ) ) == 2
    assert result.get( "recent_notes" )[ 0 ].object_id == self.note2.object_id
    assert result.get( "recent_notes" )[ 1 ].object_id == self.note.object_id

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_as_preview_viewer_with_viewer_access( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?preview=viewer" % self.anon_notebook.object_id,
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 1
    assert result.get( u"notebooks" )[ 0 ].object_id == self.anon_notebook.object_id
    assert result.get( u"notebooks" )[ 0 ].read_write == False
    assert result.get( u"notebooks" )[ 0 ].owner == False
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.anon_notebook.object_id
    assert result.get( u"notebook" ).read_write == False
    assert result.get( u"notebook" ).owner == False
    assert len( result.get( u"startup_notes" ) ) == 0
    assert result[ "total_notes_count" ] == 0
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert not result.get( "recent_notes" )
    assert len( result[ "invites" ] ) == 0

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_as_preview_collaborator_with_viewer_access( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?preview=collaborator" % self.anon_notebook.object_id,
      session_id = self.session_id,
    )
    
    # even though a collaborator preview is being requested, this user only has preview-level
    # access. so read_write should be False on the returned notebook
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 1
    assert result.get( u"notebooks" )[ 0 ].object_id == self.anon_notebook.object_id
    assert result.get( u"notebooks" )[ 0 ].read_write == False
    assert result.get( u"notebooks" )[ 0 ].owner == False
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.anon_notebook.object_id
    assert result.get( u"notebook" ).read_write == False
    assert result.get( u"notebook" ).owner == False
    assert len( result.get( u"startup_notes" ) ) == 0
    assert result[ "total_notes_count" ] == 0
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert not result.get( "recent_notes" )
    assert len( result[ "invites" ] ) == 0

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_as_preview_owner_with_viewer_access( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?preview=owner" % self.anon_notebook.object_id,
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 1 ].object_id == self.anon_notebook.object_id
    assert result.get( u"notebooks" )[ 1 ].read_write == False
    assert result.get( u"notebooks" )[ 1 ].owner == False
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.anon_notebook.object_id
    assert result.get( u"notebook" ).read_write == False
    assert result.get( u"notebook" ).owner == False
    assert len( result.get( u"startup_notes" ) ) == 0
    assert result[ "total_notes_count" ] == 0
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert not result.get( "recent_notes" )
    assert len( result[ "invites" ] ) == 0

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_as_preview_viewer_without_login( self ):
    path = "/notebooks/%s?preview=viewer" % self.notebook.object_id
    result = self.http_get( path )
    
    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def test_default_as_preview_collaborator_without_login( self ):
    path = "/notebooks/%s?preview=collaborator" % self.notebook.object_id
    result = self.http_get( path )
    
    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def test_default_as_preview_owner_without_login( self ):
    path = "/notebooks/%s?preview=owner" % self.notebook.object_id
    result = self.http_get( path )
    
    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def test_default_as_preview_viewer_without_access( self ):
    self.make_extra_notebooks()
    self.login2()

    result = self.http_get(
      "/notebooks/%s?preview=viewer" % self.notebook2.object_id,
      session_id = self.session_id,
    )
    
    assert u"access" in result.get( u"error" )

  def test_default_as_preview_collaborator_without_access( self ):
    self.make_extra_notebooks()
    self.login2()

    result = self.http_get(
      "/notebooks/%s?preview=collaborator" % self.notebook2.object_id,
      session_id = self.session_id,
    )
    
    assert u"access" in result.get( u"error" )

  def test_default_as_preview_owner_without_access( self ):
    self.make_extra_notebooks()
    self.login2()

    result = self.http_get(
      "/notebooks/%s?preview=owner" % self.notebook2.object_id,
      session_id = self.session_id,
    )
    
    assert u"access" in result.get( u"error" )

  def test_default_with_note( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?note_id=%s" % ( self.notebook.object_id, self.note.object_id ),
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 2 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 2 ].read_write == True
    assert result.get( u"notebooks" )[ 2 ].owner == True
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == True
    assert result.get( u"notebook" ).owner == True
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2

    assert result.get( "notes" )
    assert len( result.get( "notes" ) ) == 1
    assert result.get( u"notes" )[ 0 ].object_id == self.note.object_id
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert len( result.get( "recent_notes" ) ) == 2
    assert result.get( "recent_notes" )[ 0 ].object_id == self.note2.object_id
    assert result.get( "recent_notes" )[ 1 ].object_id == self.note.object_id

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_with_note_and_revision( self ):
    self.login()

    result = self.http_get(
      "/notebooks/%s?note_id=%s&revision=%s" % (
        self.notebook.object_id,
        self.note.object_id,
        quote( unicode( self.note.revision ) ),
      ),
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 2 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 2 ].read_write == True
    assert result.get( u"notebooks" )[ 2 ].owner == True
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == True
    assert result.get( u"notebook" ).owner == True
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2

    assert result.get( "notes" )
    assert len( result.get( "notes" ) ) == 1
    assert result.get( u"notes" )[ 0 ].object_id == self.note.object_id
    assert result.get( u"notes" )[ 0 ].revision == self.note.revision
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) == False
    assert len( result.get( "recent_notes" ) ) == 2
    assert result.get( "recent_notes" )[ 0 ].object_id == self.note2.object_id
    assert result.get( "recent_notes" )[ 1 ].object_id == self.note.object_id

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_with_note_and_previous_revision( self ):
    self.login()

    previous_revision = self.note.revision
    self.note.contents = u"<h3>my title</h3>foo blah"
    self.database.save( self.note )

    result = self.http_get(
      "/notebooks/%s?note_id=%s&revision=%s&previous_revision=%s" % (
        self.notebook.object_id,
        self.note.object_id,
        quote( unicode( self.note.revision ) ),
        quote( unicode( previous_revision ) ),
      ),
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 2 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 2 ].read_write == True
    assert result.get( u"notebooks" )[ 2 ].owner == True
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == True
    assert result.get( u"notebook" ).owner == True
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2

    assert result.get( "notes" )
    assert len( result.get( "notes" ) ) == 1
    assert result.get( u"notes" )[ 0 ].object_id == self.note.object_id
    assert result.get( u"notes" )[ 0 ].revision == self.note.revision
    assert result.get( u"notes" )[ 0 ].contents == u'<h3>my title</h3><ins class="diff">foo </ins>blah'
    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) == False
    assert len( result.get( "recent_notes" ) ) == 2
    assert result.get( "recent_notes" )[ 0 ].object_id == self.note.object_id
    assert result.get( "recent_notes" )[ 1 ].object_id == self.note2.object_id

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_default_with_parent( self ):
    self.login()

    parent_id = u"foo"
    result = self.http_get(
      "/notebooks/%s?parent_id=%s" % ( self.notebook.object_id, parent_id ),
      session_id = self.session_id,
    )
    
    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"notebooks" )[ 2 ].object_id == self.notebook.object_id
    assert result.get( u"notebooks" )[ 2 ].read_write == True
    assert result.get( u"notebooks" )[ 2 ].owner == True
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert result.get( u"notebook" ).read_write == True
    assert result.get( u"notebook" ).owner == True
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2
    assert result.get( u"notes" ) == []
    assert result.get( u"parent_id" ) == parent_id
    assert result.get( u"note_read_write" ) in ( None, True )
    assert len( result.get( "recent_notes" ) ) == 2
    assert result.get( "recent_notes" )[ 0 ].object_id == self.note2.object_id
    assert result.get( "recent_notes" )[ 1 ].object_id == self.note.object_id

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "total_notes_count" ] == 2
    assert result[ "notes" ] == []

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert notebook.owner == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents_with_read_write_false( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      read_write = False,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "total_notes_count" ] == 2
    assert result[ "notes" ] == []

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == False
    assert notebook.owner == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents_with_owner_false( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      owner = False,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "total_notes_count" ] == 2
    assert result[ "notes" ] == []

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert notebook.owner == False
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents_with_note( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "total_notes_count" ] == 2

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert notebook.owner == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id

    notes = result[ "notes" ]

    assert notes
    assert len( notes ) == 1
    note = notes[ 0 ]
    assert note.object_id == self.note.object_id
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents_with_note_and_revision( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      revision = unicode( self.note.revision ),
      user_id = self.user.object_id,
    )
    self.login()

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "total_notes_count" ] == 2

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert notebook.owner == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id

    notes = result[ "notes" ]

    assert notes
    assert len( notes ) == 1
    note = notes[ 0 ]
    assert note.object_id == self.note.object_id
    assert note.revision == self.note.revision
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents_with_note_and_previous_revision( self ):
    previous_revision = self.note.revision
    self.note.contents = u"<h3>my title</h3>foo blah"
    self.database.save( self.note )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      revision = unicode( self.note.revision ),
      previous_revision = unicode( previous_revision ),
      user_id = self.user.object_id,
    )
    self.login()

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "total_notes_count" ] == 2

    invites = result[ "invites" ]
    assert len( invites ) == 1
    invite = invites[ 0 ]
    assert invite.object_id == self.invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert notebook.owner == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id

    notes = result[ "notes" ]

    assert notes
    assert len( notes ) == 1
    note = notes[ 0 ]
    assert note.object_id == self.note.object_id
    assert note.revision == self.note.revision
    assert note.contents == u'<h3>my title</h3><ins class="diff">foo </ins>blah'
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents_with_different_invites( self ):
    # create an invite with a different email address from the previous
    invite = Invite.create(
      self.database.next_id( Invite ), self.user.object_id, self.notebook.object_id,
      u"smoking@example.com", read_write = True, owner = False,
    )
    self.database.save( invite )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "total_notes_count" ] == 2
    assert result[ "notes" ] == []

    invites = result[ "invites" ]
    assert len( invites ) == 2
    assert invites[ 0 ].object_id == self.invite.object_id
    assert invites[ 1 ].object_id == invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert notebook.owner == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_contents_with_duplicate_invites( self ):
    # create an invite with the same email address as the previous invite
    invite = Invite.create(
      self.database.next_id( Invite ), self.user.object_id, self.notebook.object_id,
      u"skinner@example.com", read_write = True, owner = False,
    )
    self.database.save( invite )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "total_notes_count" ] == 2
    assert result[ "notes" ] == []

    invites = result[ "invites" ]
    assert len( invites ) == 2
    assert invites[ 0 ].object_id == self.invite.object_id
    assert invites[ 1 ].object_id == invite.object_id

    assert notebook.object_id == self.notebook.object_id
    assert notebook.read_write == True
    assert notebook.owner == True
    assert len( startup_notes ) == 1
    assert startup_notes[ 0 ].object_id == self.note.object_id
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  @raises( Access_error )
  def test_contents_without_user_id( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
    )

  @raises( Access_error )
  def test_contents_with_incorrect_user_id( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.anonymous.object_id,
    )

  @raises( Access_error )
  def test_contents_with_unknown_notebook_id( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.unknown_notebook_id,
      user_id = self.user.object_id,
    )

  def test_contents_with_read_only_notebook( self ):
    result = cherrypy.root.notebooks.contents(
      notebook_id = self.anon_notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    startup_notes = result[ "startup_notes" ]
    assert result[ "notes" ] == []
    assert result[ "total_notes_count" ] == 0
    assert result[ "invites" ] == []

    assert notebook.object_id == self.anon_notebook.object_id
    assert notebook.read_write == False
    assert notebook.owner == False
    assert len( startup_notes ) == 0
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_updates( self ):
    self.login()

    result = self.http_get(
      "/notebooks/updates/%s?rss&notebook_name=%s" % ( self.notebook.object_id, self.notebook.name ),
      session_id = self.session_id,
    )

    assert len( result[ u"recent_notes" ] ) == 2
    assert result[ u"recent_notes" ][ 0 ] == ( self.note2.object_id, self.note2.revision )
    assert result[ u"recent_notes" ][ 1 ] == ( self.note.object_id, self.note.revision )
    assert result[ u"notebook_id" ] == self.notebook.object_id
    assert result[ u"notebook_name" ] == self.notebook.name
    assert result[ u"https_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ]

  def test_updates_without_login( self ):
    result = self.http_get(
      "/notebooks/updates/%s?rss&notebook_name=%s" % ( self.notebook.object_id, self.notebook.name ),
    )

    # still should get the full results even without a login
    assert len( result[ u"recent_notes" ] ) == 2
    assert result[ u"recent_notes" ][ 0 ] == ( self.note2.object_id, self.note2.revision )
    assert result[ u"recent_notes" ][ 1 ] == ( self.note.object_id, self.note.revision )
    assert result[ u"notebook_id" ] == self.notebook.object_id
    assert result[ u"notebook_name" ] == self.notebook.name
    assert result[ u"https_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ]

  def test_updates_without_access( self ):
    self.make_extra_notebooks()
    self.login2()

    result = self.http_get(
      "/notebooks/updates/%s?rss&notebook_name=%s" % ( self.notebook2.object_id, self.notebook2.name ),
      session_id = self.session_id,
    )

    # still should get the full results even without access
    assert len( result[ u"recent_notes" ] ) == 0
    assert result[ u"notebook_id" ] == self.notebook2.object_id
    assert result[ u"notebook_name" ] == self.notebook2.name
    assert result[ u"https_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ]

  def test_updates_with_unknown_notebook( self ):
    result = self.http_get(
      "/notebooks/updates/%s?rss&notebook_name=%s" % ( self.unknown_notebook_id, self.notebook.name ),
    )

    # should return no notes (and not raise an error)
    assert len( result[ u"recent_notes" ] ) == 0
    assert result[ u"notebook_id" ] == self.unknown_notebook_id
    assert result[ u"notebook_name" ] == self.notebook.name
    assert result[ u"https_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ]

  def test_updates_with_incorrect_notebook_name( self ):
    result = self.http_get(
      "/notebooks/updates/%s?rss&notebook_name=%s" % ( self.notebook.object_id, "whee" ),
    )

    # still produces results even with an incorrect notebook name
    assert len( result[ u"recent_notes" ] ) == 2
    assert result[ u"recent_notes" ][ 0 ] == ( self.note2.object_id, self.note2.revision )
    assert result[ u"recent_notes" ][ 1 ] == ( self.note.object_id, self.note.revision )
    assert result[ u"notebook_id" ] == self.notebook.object_id
    assert result[ u"notebook_name" ] == u"whee"
    assert result[ u"https_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ]

  def test_get_update_link( self ):
    self.login()

    result = self.http_get(
      "/notebooks/get_update_link?%s" % urllib.urlencode( [
        ( "notebook_id", self.notebook.object_id ),
        ( "notebook_name", self.notebook.name ),
        ( "note_id", self.note.object_id ),
        ( "revision", str( self.note.revision ) ),
      ] ),
      session_id = self.session_id,
    )

    assert result[ u"notebook_id" ] == self.notebook.object_id
    assert result[ u"notebook_name" ] == self.notebook.name
    assert result[ u"note_id" ] == self.note.object_id
    assert result[ u"https_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ]

  def test_get_update_link_without_login( self ):
    result = self.http_get(
      "/notebooks/get_update_link?%s" % urllib.urlencode( [
        ( "notebook_id", self.notebook.object_id ),
        ( "notebook_name", self.notebook.name ),
        ( "note_id", self.note.object_id ),
        ( "revision", str( self.note.revision ) ),
      ] ),
    )

    assert result[ u"notebook_id" ] == self.notebook.object_id
    assert result[ u"notebook_name" ] == self.notebook.name
    assert result[ u"note_id" ] == self.note.object_id
    assert result[ u"https_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ]

  def test_get_update_link_without_access( self ):
    self.make_extra_notebooks()
    self.login2()

    result = self.http_get(
      "/notebooks/get_update_link?%s" % urllib.urlencode( [
        ( "notebook_id", self.notebook2.object_id ),
        ( "notebook_name", self.notebook2.name ),
        ( "note_id", self.note.object_id ),
        ( "revision", str( self.note.revision ) ),
      ] ),
      session_id = self.session_id,
    )

    assert result[ u"notebook_id" ] == self.notebook2.object_id
    assert result[ u"notebook_name" ] == self.notebook2.name
    assert result[ u"note_id" ] == self.note.object_id
    assert result[ u"https_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ]

  def test_load_note( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == self.note.title
    assert note.contents == self.note.contents
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_with_revision( self ):
    self.login()

    # update the note to generate a new revision
    previous_revision = self.note.revision
    previous_title = self.note.title
    previous_contents = self.note.contents
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
    ), session_id = self.session_id )

    # load the note by the old revision
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      revision = previous_revision,
    ), session_id = self.session_id )

    note = result[ "note" ]

    # assert that we get the previous revision of the note, not the new one
    assert note.object_id == self.note.object_id
    assert note.revision == previous_revision
    assert note.title == previous_title
    assert note.contents == previous_contents
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_with_previous_revision( self ):
    self.login()

    # update the note to generate a new revision
    previous_revision = self.note.revision
    previous_title = self.note.title
    previous_contents = self.note.contents
    new_note_contents = u"<h3>my title</h3>foo blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = False,
      previous_revision = self.note.revision,
    ), session_id = self.session_id )

    new_revision = result[ "new_revision" ].revision

    # load the note by the new revision, providing the previous revision as well
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      revision = unicode( new_revision ),
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    note = result[ "note" ]

    # assert that we get a composite diff of the two revisions
    assert note.object_id == self.note.object_id
    assert note.revision == new_revision
    assert note.title == previous_title
    assert note.contents == u'<h3>my title</h3><ins class="diff">foo </ins>blah'
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0

  def test_load_note_without_login( self ):
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_load_note_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.unknown_notebook_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_with_incorrect_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.anon_notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_unknown_note( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.unknown_note_id,
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_without_notebook( self ):
    self.login()

    self.note.notebook_id = None
    self.database.save( self.note )

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_with_summary( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      summarize = True,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == self.note.title
    assert note.contents == self.note.contents
    assert note.summary == u"blah"
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_by_title( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == self.note.title
    assert note.contents == self.note.contents
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_by_title_case_insensitive( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title.upper(),
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == self.note.title
    assert note.contents == self.note.contents
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_by_title_without_login( self ):
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "error" )
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_by_title_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.unknown_notebook_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "error" )
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_unknown_note_by_title( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "unknown title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_by_title_with_summary( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title,
      summarize = True,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == self.note.title
    assert note.contents == self.note.contents
    assert note.summary == u"blah"
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_summarize_note( self ):
    note = cherrypy.root.notebooks.summarize_note( self.note )

    assert note.summary == u"blah"

  def test_summarize_note_truncated_at_word_boundary( self ):
    self.note.contents = u"<h3>the title</h3>" + u"foo bar baz quux " * 10
    note = cherrypy.root.notebooks.summarize_note( self.note )

    assert note.summary == u"foo bar baz quux foo bar baz quux foo ..."

  def test_summarize_note_truncated_at_character_boundary( self ):
    self.note.contents = u"<h3>the title</h3>" + u"foobarbazquux" * 10
    note = cherrypy.root.notebooks.summarize_note( self.note )

    assert note.summary == u"foobarbazquuxfoobarbazquuxfoobarbazquuxf ..."

  def test_summarize_note_with_short_words( self ):
    self.note.contents = u"<h3>the title</h3>" + u"a b c d e f g h i j k l"
    note = cherrypy.root.notebooks.summarize_note( self.note )

    assert note.summary == u"a b c d e f g h i j ..."

  def test_summarize_note_without_title( self ):
    self.note.contents = "foo bar baz quux"
    note = cherrypy.root.notebooks.summarize_note( self.note )

    assert note.summary == u"foo bar baz quux"

  def test_summarize_note_without_contents( self ):
    self.note.contents = None
    note = cherrypy.root.notebooks.summarize_note( self.note )

    assert note.summary == None

  def test_summarize_note_none( self ):
    note = cherrypy.root.notebooks.summarize_note( None )

    assert note == None

  def test_summarize_note_with_highligh_text( self ):
    note = cherrypy.root.notebooks.summarize_note( self.note, highlight_text = "la" )

    assert note.summary == u"b<b>la</b>h"

  def test_lookup_note_id( self ):
    self.login()

    result = self.http_post( "/notebooks/lookup_note_id/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "note_id" ) == self.note.object_id
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_lookup_note_id_case_insensitive( self ):
    self.login()

    result = self.http_post( "/notebooks/lookup_note_id/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title.upper(),
    ), session_id = self.session_id )

    assert result.get( "note_id" ) == self.note.object_id
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_lookup_note_id_without_login( self ):
    result = self.http_post( "/notebooks/lookup_note_id/", dict(
      notebook_id = self.notebook.object_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "error" )
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_lookup_note_id_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/lookup_note_id/", dict(
      notebook_id = self.unknown_notebook_id,
      note_title = self.note.title,
    ), session_id = self.session_id )

    assert result.get( "error" )
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_lookup_unknown_note_id( self ):
    self.login()

    result = self.http_post( "/notebooks/lookup_note_id/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "unknown title",
    ), session_id = self.session_id )

    assert result.get( "note_id" ) == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_load_note_revisions( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_revisions/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    revisions = result[ "revisions" ]
    assert revisions != None
    assert len( revisions ) == 2
    assert revisions[ 1 ].revision == self.note.revision
    assert revisions[ 1 ].user_id == self.user.object_id
    assert revisions[ 1 ].username == self.username

  def test_load_note_links( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    html = result.get( "tree_html" )
    assert u"<table"
    assert u"<a href=" not in html
    assert u"tree_expander" not in html

  def test_load_note_links_with_external_link( self ):
    self.login()

    link = u'<a href="http://example.com/link" target="_new"%s>link</a>'
    self.note.contents = u"<h3>blah</h3> this is a %s" % ( link % "" )
    self.database.save( self.note )

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    html = result.get( "tree_html" )
    assert u"<table"
    assert link % u' class="note_tree_external_link"' in html
    assert u"tree_expander_empty" in html

  def test_load_note_links_with_file_link( self ):
    self.login()

    link = u'<a href="../../files/fileid?blah"%s>link to file</a>'
    self.note.contents = u"<h3>blah</h3> this is a %s" % ( link % "" )
    self.database.save( self.note )

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    html = result.get( "tree_html" )
    assert u"<table"
    assert link % u' target="_new" class="note_tree_file_link"' in html
    assert u"tree_expander_empty" in html

  def test_load_note_links_with_embedded_image_file_link( self ):
    self.login()

    link = u'<a href="../../files/fileid?blah"%s><img src="/blah"></a>'
    self.note.contents = u"<h3>blah</h3> this is a %s" % ( link % "" )
    self.database.save( self.note )

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    html = result.get( "tree_html" )
    assert u"<table"
    assert u'<a href="../../files/fileid?blah" target="_new" class="note_tree_file_link">embedded image</a>' in html
    assert u"tree_expander_empty" in html

  def test_load_note_links_with_new_file_link( self ):
    self.login()

    link = u'<a href="../../files/new"%s>link to new file</a>'
    self.note.contents = u"<h3>blah</h3> this is a %s" % ( link % "" )
    self.database.save( self.note )

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    html = result.get( "tree_html" )
    assert u"<table"
    assert link % u' target="_new" class="note_tree_file_link"' not in html
    assert u"tree_expander_empty" not in html

  def test_load_note_links_with_note_link( self ):
    self.login()

    link = u'<a href="/notebooks/nbid?note_id=' + self.note2.object_id + '"%s>link to note2</a>'
    self.note.contents = u"<h3>blah</h3> this is a %s" % ( link % "" )
    self.database.save( self.note )

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    html = result.get( "tree_html" )
    assert u"<table"
    assert link % u' class="note_tree_link"' in html
    assert u"tree_expander_empty" in html

  def test_load_note_links_of_note_in_trash( self ):
    self.login()

    link = u'<a href="/notebooks/nbid?note_id=' + self.note2.object_id + '"%s>link to note2</a>'
    self.note.contents = u"<h3>blah</h3> this is a %s" % ( link % "" )
    self.note.deleted_from_id = self.note.notebook_id
    self.note.notebook_id = self.trash.object_id
    self.database.save( self.note )

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    html = result.get( "tree_html" )
    assert u"<table"
    assert link % u' class="note_tree_link"' in html
    assert u"tree_expander_empty" in html

  def test_load_note_links_with_note_link_with_uppercase_tags( self ):
    self.login()

    link = u'<A HREF="/notebooks/nbid?note_id=' + self.note2.object_id + '"%s>link to note2</A>'
    self.note.contents = u"<h3>blah</h3> this is a %s" % ( link % "" )
    self.database.save( self.note )

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    html = result.get( "tree_html" )
    assert u"<table"
    link = u'<a HREF="/notebooks/nbid?note_id=' + self.note2.object_id + '"%s>link to note2</a>'
    assert link % u' class="note_tree_link"' in html
    assert u"tree_expander_empty" in html

  def test_load_note_links_with_note_link_to_unknown_note_id( self ):
    self.login()

    link = u'<a href="/notebooks/nbid?note_id=' + self.unknown_note_id + '"%s>link to note2</a>'
    self.note.contents = u"<h3>blah</h3> this is a %s" % ( link % "" )
    self.database.save( self.note )

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    html = result.get( "tree_html" )
    assert u"<table"
    assert link % u' class="note_tree_link"' in html
    assert u"tree_expander_empty" in html

  def test_load_note_links_with_note_link_with_children( self ):
    self.login()

    link = u'<a href="/notebooks/nbid?note_id=' + self.note2.object_id + '"%s>link to note2</a>'
    self.note.contents = u"<h3>blah</h3> this is a %s" % ( link % "" )
    self.database.save( self.note )

    link2 = u'<a href="/notebooks/nbid?note_id=' + self.note.object_id + '"%s>link back to note</a>'
    self.note2.contents = u"<h3>blah</h3> this is a %s" % ( link % "" )
    self.database.save( self.note2 )

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    html = result.get( "tree_html" )
    assert u"<table"
    assert link % u' class="note_tree_link"' in html
    assert u"tree_expander" in html

  def test_load_note_links_with_multiple_links( self ):
    self.login()

    link = u'<a href="/notebooks/nbid?note_id=' + self.note2.object_id + '"%s>link to note2</a>'
    link2 = u'<a href="/notebooks/nbid?note_id=' + self.note.object_id + '"%s>link to self</a>'
    external_link = u'<a href="/link" target="_top"%s>link</a>'
    file_link = u'<a href="/files/fileid"%s>link to file</a>'
    self.note.contents = u"<h3>blah</h3> %s and %s and %s and %s as well" % (
      link % "", link2 % "", external_link % "", file_link % "",
    )
    self.database.save( self.note )

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    html = result.get( "tree_html" )
    assert u"<table"
    assert link % u' class="note_tree_link"' in html
    assert link2 % u' class="note_tree_link"' in html
    assert external_link % u' class="note_tree_external_link"' in html
    assert file_link % u' target="_new" class="note_tree_file_link"' in html
    assert u"tree_expander_empty" in html

  def test_load_note_links_without_login( self ):
    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ) )

    assert u"access" in result.get( u"error" )

  def test_load_note_links_without_access( self ):
    self.make_extra_notebooks()
    self.login2()

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.notebook2.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert u"access" in result.get( u"error" )

  def test_load_note_links_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.unknown_notebook_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert u"access" in result.get( u"error" )

  def test_load_note_links_with_unknown_note_id( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.unknown_note_id,
    ), session_id = self.session_id )

    assert u"access" in result.get( u"error" )

  def test_load_note_links_with_note_in_incorrect_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/load_note_links/", dict(
      notebook_id = self.anon_notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert u"access" in result.get( u"error" )

  def test_save_note( self, startup = False ):
    self.login()

    # save over an existing note, supplying new contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    assert result[ "new_revision" ]
    assert result[ "new_revision" ].revision != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    current_revision = result[ "new_revision" ].revision
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # make sure the old title can no longer be loaded
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "my title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == "new title"
    assert note.contents == new_note_contents
    assert note.startup == startup
    assert note.user_id == self.user.object_id

    if startup:
      assert note.rank == 0 
    else:
      assert note.rank is None

    # make sure that the correct revisions are returned and are in chronological order
    result = self.http_post( "/notebooks/load_note_revisions/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    revisions = result[ "revisions" ]
    assert revisions != None
    assert len( revisions ) == 3
    assert revisions[ 1 ].revision == previous_revision
    assert revisions[ 1 ].user_id == self.user.object_id
    assert revisions[ 1 ].username == self.username
    assert revisions[ 2 ].revision == current_revision
    assert revisions[ 2 ].user_id == self.user.object_id
    assert revisions[ 2 ].username == self.username

  def test_save_startup_note( self ):
    self.test_save_note( startup = True )

  def test_save_note_by_different_user( self, startup = False ):
    self.login2()

    # save over an existing note as a different user, supplying new contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    assert result[ "new_revision" ]
    assert result[ "new_revision" ].revision != previous_revision
    assert result[ "new_revision" ].user_id == self.user2.object_id
    assert result[ "new_revision" ].username == self.username2
    current_revision = result[ "new_revision" ].revision
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username

    self.login()

    # make sure the old title can no longer be loaded
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "my title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == "new title"
    assert note.contents == new_note_contents
    assert note.startup == startup
    assert note.user_id == self.user2.object_id

    if startup:
      assert note.rank == 0 
    else:
      assert note.rank is None

    # make sure that the correct revisions are returned and are in chronological order
    result = self.http_post( "/notebooks/load_note_revisions/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    revisions = result[ "revisions" ]
    assert revisions != None
    assert len( revisions ) == 3
    assert revisions[ 1 ].revision == previous_revision
    assert revisions[ 1 ].user_id == self.user.object_id
    assert revisions[ 1 ].username == self.username
    assert revisions[ 2 ].revision == current_revision
    assert revisions[ 2 ].user_id == self.user2.object_id
    assert revisions[ 2 ].username == self.username2

  def test_save_note_without_login( self, startup = False ):
    # save over an existing note supplying new contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    assert result.get( "error" )
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_save_startup_note_without_login( self ):
    self.test_save_note_without_login( startup = True )

  def test_save_note_too_long( self, startup = False ):
    self.login()

    # save over an existing note supplying new (too long) contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah" * 962
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    assert result.get( "error" )
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_save_note_too_long_before_cleaning( self, startup = False ):
    self.login()

    # save over an existing note supplying new contents and a new title. the contents
    # should be too long before they're cleaned/stripped, but short enough after
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3><span>ha" * 962
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    assert result[ "new_revision" ]
    assert result[ "new_revision" ].revision != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    current_revision = result[ "new_revision" ].revision
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # make sure the old title can no longer be loaded
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "my title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == "new title"
    assert note.contents == new_note_contents.replace( u"<span>", "" )
    assert note.startup == startup
    assert note.user_id == self.user.object_id

    if startup:
      assert note.rank == 0 
    else:
      assert note.rank is None

    # make sure that the correct revisions are returned and are in chronological order
    result = self.http_post( "/notebooks/load_note_revisions/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    revisions = result[ "revisions" ]
    assert revisions != None
    assert len( revisions ) == 3
    assert revisions[ 1 ].revision == previous_revision
    assert revisions[ 1 ].user_id == self.user.object_id
    assert revisions[ 1 ].username == self.username
    assert revisions[ 2 ].revision == current_revision
    assert revisions[ 2 ].user_id == self.user.object_id
    assert revisions[ 2 ].username == self.username

  def test_save_deleted_note( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    # save over a deleted note, supplying new contents and a new title. this should cause the note
    # to be automatically undeleted
    deleted_note = self.database.load( Note, self.note.object_id )
    previous_revision = deleted_note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = False,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    assert result[ "new_revision" ]
    assert result[ "new_revision" ].revision != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # make sure the old title can no longer be loaded
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "my title",
    ), session_id = self.session_id )

    assert result[ "note" ] == None

    # make sure the new title is now loadable from the notebook
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note
    assert note.object_id == self.note.object_id
    assert note.title == "new title"
    assert note.contents == new_note_contents
    assert note.deleted_from_id == None
    assert note.user_id == self.user.object_id

    # make sure the old title can no longer be loaded from the trash
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.trash_id,
      note_title = "my title",
    ), session_id = self.session_id )

    assert result[ "note" ] == None

    # make sure the new title is not loadable from the trash either
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.trash_id,
      note_title = "new title",
    ), session_id = self.session_id )

    assert result[ "note" ] == None

  def test_save_unchanged_note( self, startup = False ):
    self.login()

    # save over an existing note, supplying new contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # now attempt to save over that note again without changing the contents
    user = self.database.load( User, self.user.object_id )
    previous_storage_bytes = user.storage_bytes
    previous_revision = result[ "new_revision" ].revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # assert that the note wasn't actually updated the second time
    assert result[ "new_revision" ] == None
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == previous_storage_bytes
    assert result[ "storage_bytes" ] == 0

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note
    assert note.object_id == self.note.object_id
    assert note.title == "new title"
    assert note.contents == new_note_contents
    assert note.user_id == self.user.object_id
    assert note.revision == previous_revision

  def test_save_unchanged_deleted_note( self, startup = False ):
    self.login()

    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    # save over an existing deleted note, supplying new contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # now attempt to save over that note again without changing the contents
    user = self.database.load( User, self.user.object_id )
    previous_storage_bytes = user.storage_bytes
    previous_revision = result[ "new_revision" ].revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # assert that the note wasn't actually updated the second time
    assert result[ "new_revision" ] == None
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == previous_storage_bytes
    assert result[ "storage_bytes" ] == 0

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note
    assert note.object_id == self.note.object_id
    assert note.title == "new title"
    assert note.contents == new_note_contents
    assert note.user_id == self.user.object_id
    assert note.revision == previous_revision
    assert note.deleted_from_id == None

    # make sure the note is not loadable from the trash
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.trash_id,
      note_title = "new title",
    ), session_id = self.session_id )

    assert result[ "note" ] == None

  def test_save_unchanged_note_with_startup_change( self, startup = False ):
    self.login()

    # save over an existing note supplying new contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # now attempt to save over that note again without changing the contents, but with a change
    # to its startup flag
    previous_revision = result[ "new_revision" ].revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = not startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # assert that the note was updated the second time
    assert result[ "new_revision" ]
    assert result[ "new_revision" ].revision != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note
    assert note.object_id == self.note.object_id
    assert note.title == "new title"
    assert note.contents == new_note_contents
    assert note.user_id == self.user.object_id
    assert note.revision > previous_revision
    assert note.startup == ( not startup )

    if note.startup:
      assert note.rank == 0 
    else:
      assert note.rank is None

  def test_save_unchanged_note_with_extra_newline( self, startup = False ):
    self.login()

    # save over an existing note, supplying new contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # now attempt to save over that note again without changing the contents,
    # except for adding a newline
    user = self.database.load( User, self.user.object_id )
    previous_storage_bytes = user.storage_bytes
    previous_revision = result[ "new_revision" ].revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents + u"\n",
      startup = startup,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    # assert that the note wasn't actually updated the second time
    assert result[ "new_revision" ] == None
    assert result[ "previous_revision" ].revision == previous_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == previous_storage_bytes
    assert result[ "storage_bytes" ] == 0

    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note
    assert note.object_id == self.note.object_id
    assert note.title == "new title"
    assert note.contents == new_note_contents
    assert note.user_id == self.user.object_id
    assert note.revision == previous_revision

  def test_save_note_from_an_older_revision( self ):
    self.login()

    # save over an existing note supplying new contents and a new title
    first_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = False,
      previous_revision = first_revision,
    ), session_id = self.session_id )

    # save over that note again with new contents, providing the original
    # revision as the previous known revision
    second_revision = result[ "new_revision" ].revision
    new_note_contents = u"<h3>new new title</h3>new new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = False,
      previous_revision = first_revision,
    ), session_id = self.session_id )

    # make sure the second save actually caused an update
    assert result[ "new_revision" ]
    assert result[ "new_revision" ].revision not in ( first_revision, second_revision )
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    assert result[ "previous_revision" ].revision == second_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # make sure the first title can no longer be loaded
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "my title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None

    # make sure the second title can no longer be loaded
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new title",
    ), session_id = self.session_id )

    note = result[ "note" ]
    assert note == None

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = "new new title",
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == self.note.object_id
    assert note.title == "new new title"
    assert note.contents == new_note_contents
    assert note.user_id == self.user.object_id

  def test_save_note_with_unknown_notebook( self ):
    self.login()

    # save over an existing note supplying new contents and a new title
    previous_revision = self.note.revision
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.unknown_notebook_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = False,
      previous_revision = previous_revision,
    ), session_id = self.session_id )

    assert result.get( "error" )
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_save_new_note( self, startup = False ):
    self.login()

    # save a completely new note
    new_note = Note.create( "55", u"<h3>newest title</h3>foo" )
    previous_revision = new_note.revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = new_note.object_id,
      contents = new_note.contents,
      startup = startup,
      previous_revision = None,
    ), session_id = self.session_id )

    assert result[ "new_revision" ]
    assert result[ "new_revision" ] != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    assert result[ "previous_revision" ] == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = new_note.title,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == new_note.object_id
    assert note.title == new_note.title
    assert note.contents == new_note.contents
    assert note.startup == startup
    assert note.user_id == self.user.object_id

    if startup:
      assert note.rank == 0 
    else:
      assert note.rank is None

  def test_save_new_startup_note( self ):
    self.test_save_new_note( startup = True )

  def test_save_new_note_with_disallowed_tags( self ):
    self.login()

    # save a completely new note
    title_with_tags = u"<h3>my funny title</h3>"
    junk = u"foo<script>haxx0r</script>"
    more_junk = u"<p style=\"evil\">blah</p>"
    new_note = Note.create( "55", title_with_tags + junk + more_junk )
    previous_revision = new_note.revision

    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = new_note.object_id,
      contents = new_note.contents,
      startup = False,
      previous_revision = None,
    ), session_id = self.session_id )

    assert result[ "new_revision" ]
    assert result[ "new_revision" ] != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    assert result[ "previous_revision" ] == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = new_note.title,
    ), session_id = self.session_id )

    note = result[ "note" ]

    expected_contents = title_with_tags + u"foohaxx0r<p>blah</p>"

    assert note.object_id == new_note.object_id
    assert note.title == new_note.title
    assert note.contents == expected_contents
    assert note.user_id == self.user.object_id

  def test_save_new_note_with_bad_characters( self ):
    self.login()

    # save a completely new note
    contents = "<h3>newest title</h3>foo"
    junk = "\xa0bar"
    new_note = Note.create( "55", contents + junk )
    previous_revision = new_note.revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = new_note.object_id,
      contents = new_note.contents,
      startup = False,
      previous_revision = None,
    ), session_id = self.session_id )

    assert result[ "new_revision" ]
    assert result[ "new_revision" ] != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    assert result[ "previous_revision" ] == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = new_note.title,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == new_note.object_id
    assert note.title == new_note.title
    assert note.contents == contents + " bar"
    assert note.user_id == self.user.object_id

  def test_save_two_new_notes( self, startup = False ):
    self.login()

    # save a completely new note
    new_note = Note.create( "55", u"<h3>newest title</h3>foo" )
    previous_revision = new_note.revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = new_note.object_id,
      contents = new_note.contents,
      startup = startup,
      previous_revision = None,
    ), session_id = self.session_id )

    user = self.database.load( User, self.user.object_id )
    previous_storage_bytes = user.storage_bytes

    # save a completely new note
    new_note = Note.create( "56", u"<h3>my new title</h3>foo" )
    previous_revision = new_note.revision
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = new_note.object_id,
      contents = new_note.contents,
      startup = startup,
      previous_revision = None,
    ), session_id = self.session_id )

    assert result[ "new_revision" ]
    assert result[ "new_revision" ] != previous_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    assert result[ "previous_revision" ] == None
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # make sure the new title is now loadable
    result = self.http_post( "/notebooks/load_note_by_title/", dict(
      notebook_id = self.notebook.object_id,
      note_title = new_note.title,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note.object_id == new_note.object_id
    assert note.title == new_note.title
    assert note.contents == new_note.contents
    assert note.startup == startup
    assert note.user_id == self.user.object_id

    if startup:
      assert note.rank == 1 # one greater than the previous new note's rank 
    else:
      assert note.rank is None

  def test_save_two_new_startup_notes( self ):
    self.test_save_two_new_notes( startup = True )

  def test_revert_note( self ):
    self.login()

    # save over an existing note, supplying new contents and a new title
    first_revision = self.note.revision
    original_contents = self.note.contents
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = False,
      previous_revision = first_revision,
    ), session_id = self.session_id )

    second_revision = result[ "new_revision" ].revision

    # revert the note to the earlier revision
    result = self.http_post( "/notebooks/revert_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      revision = first_revision,
    ), session_id = self.session_id )

    assert result[ "new_revision" ]
    assert result[ "new_revision" ].revision != first_revision
    assert result[ "new_revision" ].revision != second_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    current_revision = result[ "new_revision" ].revision
    assert result[ "previous_revision" ].revision == second_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes
    assert result[ "contents" ] == original_contents

    # make sure that the correct revisions are returned and are in chronological order
    result = self.http_post( "/notebooks/load_note_revisions/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    revisions = result[ "revisions" ]
    assert revisions != None
    assert len( revisions ) == 4
    assert revisions[ 1 ].revision == first_revision
    assert revisions[ 1 ].user_id == self.user.object_id
    assert revisions[ 1 ].username == self.username
    assert revisions[ 2 ].revision == second_revision
    assert revisions[ 2 ].user_id == self.user.object_id
    assert revisions[ 2 ].username == self.username
    assert revisions[ 3 ].revision == current_revision
    assert revisions[ 3 ].user_id == self.user.object_id
    assert revisions[ 3 ].username == self.username

  def test_revert_note_by_different_user( self ):
    self.login()

    # save over an existing note, supplying new contents and a new title
    first_revision = self.note.revision
    original_contents = self.note.contents
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = False,
      previous_revision = first_revision,
    ), session_id = self.session_id )

    second_revision = result[ "new_revision" ].revision

    self.login2()

    # as a different user, revert the note to the earlier revision
    result = self.http_post( "/notebooks/revert_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      revision = first_revision,
    ), session_id = self.session_id )

    assert result[ "new_revision" ]
    assert result[ "new_revision" ].revision != first_revision
    assert result[ "new_revision" ].revision != second_revision
    assert result[ "new_revision" ].user_id == self.user2.object_id
    assert result[ "new_revision" ].username == self.username2
    current_revision = result[ "new_revision" ].revision
    assert result[ "previous_revision" ].revision == second_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
    assert result[ "contents" ] == original_contents

    # make sure that the correct revisions are returned and are in chronological order
    result = self.http_post( "/notebooks/load_note_revisions/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    revisions = result[ "revisions" ]
    assert revisions != None
    assert len( revisions ) == 4
    assert revisions[ 1 ].revision == first_revision
    assert revisions[ 1 ].user_id == self.user.object_id
    assert revisions[ 1 ].username == self.username
    assert revisions[ 2 ].revision == second_revision
    assert revisions[ 2 ].user_id == self.user.object_id
    assert revisions[ 2 ].username == self.username
    assert revisions[ 3 ].revision == current_revision
    assert revisions[ 3 ].user_id == self.user2.object_id
    assert revisions[ 3 ].username == self.username2

  def test_revert_note_without_login( self ):
    self.login()

    # save over an existing note, supplying new contents and a new title
    first_revision = self.note.revision
    original_contents = self.note.contents
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = False,
      previous_revision = first_revision,
    ), session_id = self.session_id )

    second_revision = result[ "new_revision" ].revision

    # revert the note to the earlier revision, but without logging in
    result = self.http_post( "/notebooks/revert_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      revision = first_revision,
    ) )

    assert result.get( "error" )

    # make sure that a new revision wasn't saved
    result = self.http_post( "/notebooks/load_note_revisions/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    revisions = result[ "revisions" ]
    assert revisions != None
    assert len( revisions ) == 3
    assert revisions[ 1 ].revision == first_revision
    assert revisions[ 1 ].user_id == self.user.object_id
    assert revisions[ 1 ].username == self.username
    assert revisions[ 2 ].revision == second_revision
    assert revisions[ 2 ].user_id == self.user.object_id
    assert revisions[ 2 ].username == self.username

  def test_revert_deleted_note( self ):
    self.login()

    # delete an existing note
    first_revision = self.note.revision
    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = self.database.load( Note, self.note.object_id )
    second_revision = note.revision

    # revert the note to the earlier, non-deleted revision
    result = self.http_post( "/notebooks/revert_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      revision = first_revision,
    ), session_id = self.session_id )

    assert result[ "new_revision" ]
    assert result[ "new_revision" ].revision != first_revision
    assert result[ "new_revision" ].revision != second_revision
    assert result[ "new_revision" ].user_id == self.user.object_id
    assert result[ "new_revision" ].username == self.username
    current_revision = result[ "new_revision" ].revision
    assert result[ "previous_revision" ].revision == second_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes
    assert result[ "contents" ] == self.note.contents

    # make sure that the reverted note is not in the trash anymore
    note = self.database.load( Note, self.note.object_id )
    assert note.notebook_id == self.note.notebook_id

    # make sure that the correct revisions are returned and are in chronological order
    result = self.http_post( "/notebooks/load_note_revisions/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    revisions = result[ "revisions" ]
    assert revisions != None
    assert len( revisions ) == 4
    assert revisions[ 1 ].revision == first_revision
    assert revisions[ 1 ].user_id == self.user.object_id
    assert revisions[ 1 ].username == self.username
    assert revisions[ 2 ].revision == second_revision
    assert revisions[ 2 ].user_id == self.user.object_id
    assert revisions[ 2 ].username == self.username
    assert revisions[ 3 ].revision == current_revision
    assert revisions[ 3 ].user_id == self.user.object_id
    assert revisions[ 3 ].username == self.username

  def test_revert_note_with_unknown_notebook( self ):
    self.login()

    # save over an existing note, supplying new contents and a new title
    first_revision = self.note.revision
    original_contents = self.note.contents
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = False,
      previous_revision = first_revision,
    ), session_id = self.session_id )

    second_revision = result[ "new_revision" ].revision

    # revert the note to the earlier revision, but with an unknown notebook
    result = self.http_post( "/notebooks/revert_note/", dict(
      notebook_id = self.unknown_notebook_id,
      note_id = self.note.object_id,
      revision = first_revision,
    ), session_id = self.session_id )

    assert result.get( "error" )

    # make sure that a new revision wasn't saved
    result = self.http_post( "/notebooks/load_note_revisions/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    revisions = result[ "revisions" ]
    assert revisions != None
    assert len( revisions ) == 3
    assert revisions[ 1 ].revision == first_revision
    assert revisions[ 1 ].user_id == self.user.object_id
    assert revisions[ 1 ].username == self.username
    assert revisions[ 2 ].revision == second_revision
    assert revisions[ 2 ].user_id == self.user.object_id
    assert revisions[ 2 ].username == self.username

  def test_revert_unknown_note( self ):
    self.login()

    # revert a new (unsaved) note
    new_note = Note.create( "55", u"<h3>newest title</h3>foo" )
    result = self.http_post( "/notebooks/revert_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = new_note.object_id,
      revision = new_note.revision,
    ), session_id = self.session_id )

    assert "access" in result.get( "error" )

    note = self.database.load( Note, new_note.object_id )
    assert note == None

  def test_revert_note_to_newest_revision( self ):
    self.login()

    # save over an existing note, supplying new contents and a new title
    first_revision = self.note.revision
    original_contents = self.note.contents
    new_note_contents = u"<h3>new title</h3>new blah"
    result = self.http_post( "/notebooks/save_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      contents = new_note_contents,
      startup = False,
      previous_revision = first_revision,
    ), session_id = self.session_id )

    second_revision = result[ "new_revision" ].revision

    # "revert" the note to the most recent revision
    result = self.http_post( "/notebooks/revert_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      revision = second_revision,
    ), session_id = self.session_id )

    assert result[ "new_revision" ] is None
    assert result[ "previous_revision" ].revision == second_revision
    assert result[ "previous_revision" ].user_id == self.user.object_id
    assert result[ "previous_revision" ].username == self.username
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "contents" ] == new_note_contents

    # make sure that the correct revisions are returned and are in chronological order
    result = self.http_post( "/notebooks/load_note_revisions/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    revisions = result[ "revisions" ]
    assert revisions != None
    assert len( revisions ) == 3
    assert revisions[ 1 ].revision == first_revision
    assert revisions[ 1 ].user_id == self.user.object_id
    assert revisions[ 1 ].username == self.username
    assert revisions[ 2 ].revision == second_revision
    assert revisions[ 2 ].user_id == self.user.object_id
    assert revisions[ 2 ].username == self.username

  def test_delete_note( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # test that the deleted note is actually deleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result[ "note" ] is None
    assert result[ "note_id_in_trash" ] == self.note.object_id

    # test that the deleted note can be loaded from the trash
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result[ "note" ]

    assert note
    assert note.object_id == self.note.object_id
    assert note.title == self.note.title
    assert note.contents == self.note.contents
    assert note.startup == self.note.startup
    assert note.deleted_from_id == self.notebook.object_id
    assert note.user_id == self.user.object_id

  def test_delete_note_from_trash( self ):
    self.login()

    # first, delete the note from the main notebook, thereby moving it to the trash
    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # then, delete the note from the trash
    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.trash_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # test that the deleted note is actually deleted from the trash
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "note" ) is None

  def test_delete_note_without_login( self ):
    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_delete_note_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.unknown_notebook_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    # test that the note hasn't been deleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note.object_id == self.note.object_id

  def test_delete_unknown_note( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.unknown_note_id,
    ), session_id = self.session_id )

    # test that the note hasn't been deleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note.object_id == self.note.object_id

  def test_undelete_note( self ):
    self.login()

    # first delete the note
    self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    # get the revision of the deleted note
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.trash.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )
    deleted_revision = result[ "note" ].revision

    # then undelete the note
    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # test that the undeleted note is actually undeleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == None
    assert note.notebook_id == self.notebook.object_id
    assert note.user_id == self.user.object_id

    # test that the revision of the note from when it was deleted is loadable
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
      revision = deleted_revision,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == self.notebook.object_id
    assert note.notebook_id == self.trash.object_id
    assert note.user_id == self.user.object_id

  def test_undelete_note_that_is_not_deleted( self ):
    self.login()

    # "undelete" the note
    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" ) == None

    # test that the "undeleted" note is where it should be
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == None
    assert note.notebook_id == self.notebook.object_id

  def test_undelete_note_without_login( self ):
    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_undelete_note_with_unknown_notebook( self ):
    self.login()

    self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.unknown_notebook_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

    # test that the note hasn't been undeleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == self.notebook.object_id
    assert note.notebook_id == self.notebook.trash_id
    assert note.user_id == self.user.object_id

  def test_undelete_unknown_note( self ):
    self.login()

    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.unknown_note_id,
    ), session_id = self.session_id )

    # test that the note hasn't been deleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == None
    assert note.notebook_id == self.notebook.object_id
    assert note.user_id == self.user.object_id

  def test_undelete_note_from_incorrect_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.anon_notebook,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

    # test that the note hasn't been undeleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == self.notebook.object_id
    assert note.notebook_id == self.notebook.trash_id
    assert note.user_id == self.user.object_id

  def test_undelete_note_that_is_not_deleted_from_id_incorrect_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/undelete_note/", dict(
      notebook_id = self.anon_notebook,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

    # test that the note is still in its notebook
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == None
    assert note.notebook_id == self.notebook.object_id
    assert note.user_id == self.user.object_id

  def test_delete_all_notes( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_all_notes/", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # test that all notes are actually deleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result[ "note" ] is None

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note2.object_id,
    ), session_id = self.session_id )

    assert result[ "note" ] is None

    # test that all notes can be loaded from the trash
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note
    assert note.object_id == self.note.object_id
    assert note.deleted_from_id == self.notebook.object_id
    assert note.notebook_id == self.notebook.trash_id
    assert note.user_id == self.user.object_id

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash_id,
      note_id = self.note2.object_id,
    ), session_id = self.session_id )

    note2 = result.get( "note" )
    assert note2
    assert note2.object_id == self.note2.object_id
    assert note2.deleted_from_id == self.notebook.object_id
    assert note2.notebook_id == self.notebook.trash_id
    assert note2.user_id == self.user.object_id

  def test_delete_all_notes_from_trash( self ):
    self.login()

    # first, delete all notes from the main notebook, thereby moving them to the trash
    result = self.http_post( "/notebooks/delete_all_notes/", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    # then, delete all notes from the trash
    result = self.http_post( "/notebooks/delete_all_notes/", dict(
      notebook_id = self.notebook.trash_id,
    ), session_id = self.session_id )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0
    assert result[ "storage_bytes" ] == user.storage_bytes

    # test that all notes are actually deleted from the trash
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.trash_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    assert result.get( "note" ) is None

  def test_delete_all_notes_without_login( self ):
    result = self.http_post( "/notebooks/delete_all_notes/", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_delete_all_notes_with_unknown_notebook( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_all_notes/", dict(
      notebook_id = self.unknown_notebook_id,
    ), session_id = self.session_id )

    # test that the notes haven't been deleted
    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note.object_id,
    ), session_id = self.session_id )

    note = result.get( "note" )
    assert note.object_id == self.note.object_id

    result = self.http_post( "/notebooks/load_note/", dict(
      notebook_id = self.notebook.object_id,
      note_id = self.note2.object_id,
    ), session_id = self.session_id )

    note2 = result.get( "note" )
    assert note2.object_id == self.note2.object_id

  def test_search_note_titles( self ):
    self.login()

    search_text = u"other"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note2.object_id

  def test_search_contents( self ):
    self.login()

    search_text = u"bla"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note.object_id
    assert notes[ 0 ].summary

  def test_search_without_login( self ):
    search_text = u"bla"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_search_without_access( self ):
    self.login2()
    self.make_extra_notebooks()

    search_text = u"other"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook2.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_search_case_insensitive( self ):
    self.login()

    search_text = u"bLA"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note.object_id
    assert notes[ 0 ].summary

  def test_search_empty( self ):
    self.login()

    search_text = ""

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    assert result[ "error" ]
    assert u"missing" in result[ "error" ]

  def test_search_long( self ):
    self.login()

    search_text = "w" * 257

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    assert result[ "error" ]
    assert u"too long" in result[ "error" ]

  def test_search_with_no_results( self ):
    self.login()

    search_text = "doesn't match anything"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 0

  def test_search_note_title_and_contents( self ):
    self.login()

    # ensure that notes with titles matching the search text show up before notes with only
    # contents matching the search text
    note3 = Note.create( "55", u"<h3>blah</h3>foo", notebook_id = self.notebook.object_id )
    self.database.save( note3 )

    search_text = "bla"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 2
    assert notes[ 0 ].object_id == note3.object_id
    assert notes[ 0 ].summary
    assert notes[ 1 ].object_id == self.note.object_id
    assert notes[ 1 ].summary

  def test_search_character_refs( self ):
    self.login()

    note3 = Note.create( "55", u"<h3>foo: bar</h3>baz", notebook_id = self.notebook.object_id )
    self.database.save( note3 )

    search_text = "oo: b"

    result = self.http_post( "/notebooks/search/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == note3.object_id
    assert notes[ 0 ].summary

  def test_search_titles( self ):
    self.login()

    search_text = u"other"

    result = self.http_post( "/notebooks/search_titles/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note2.object_id
    assert notes[ 0 ].title == self.note2.title
    assert notes[ 0 ].summary == self.note2.title.replace( search_text, u"<b>%s</b>" % search_text )

  def test_search_titles_without_login( self ):
    search_text = u"other"

    result = self.http_post( "/notebooks/search_titles/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ) )

    assert result.get( "error" )

  def test_search_titles_without_access( self ):
    self.login2()
    self.make_extra_notebooks()

    search_text = u"other"

    result = self.http_post( "/notebooks/search_titles/", dict(
      notebook_id = self.notebook2.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_search_titles_multiple( self ):
    self.login()

    search_text = u"itl"

    result = self.http_post( "/notebooks/search_titles/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 2
    assert notes[ 0 ].object_id == self.note2.object_id
    assert notes[ 0 ].title == self.note2.title
    assert notes[ 0 ].summary == self.note2.title.replace( search_text, u"<b>%s</b>" % search_text )
    assert notes[ 1 ].object_id == self.note.object_id
    assert notes[ 1 ].title == self.note.title
    assert notes[ 1 ].summary == self.note.title.replace( search_text, u"<b>%s</b>" % search_text )

  def test_search_titles_case_insensitive( self ):
    self.login()

    search_text = u"oTHer"

    result = self.http_post( "/notebooks/search_titles/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note2.object_id
    assert notes[ 0 ].title == self.note2.title
    assert notes[ 0 ].summary == u"<b>other</b> title"

  def test_search_titles_empty( self ):
    self.login()

    search_text = ""

    result = self.http_post( "/notebooks/search_titles/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert result[ "error" ]
    assert u"missing" in result[ "error" ]

  def test_search_titles_long( self ):
    self.login()

    search_text = "w" * 257

    result = self.http_post( "/notebooks/search_titles/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert result[ "error" ]
    assert u"too long" in result[ "error" ]

  def test_search_titles_with_no_results( self ):
    self.login()

    search_text = "doesn't match anything"

    result = self.http_post( "/notebooks/search_titles/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 0

  def test_search_titles_character_refs( self ):
    self.login()

    note3 = Note.create( "55", u"<h3>foo: bar</h3>baz", notebook_id = self.notebook.object_id )
    self.database.save( note3 )

    search_text = "oo: b"

    result = self.http_post( "/notebooks/search_titles/", dict(
      notebook_id = self.notebook.object_id,
      search_text = search_text,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 1
    assert notes[ 0 ].object_id == note3.object_id

  def test_all_notes( self ):
    self.login()

    result = self.http_post( "/notebooks/all_notes/", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    notes = result.get( "notes" )

    assert len( notes ) == 2
    assert notes[ 0 ][ 0 ] == self.note2.object_id
    assert notes[ 0 ][ 1 ] == self.note2.title
    assert notes[ 1 ][ 0 ] == self.note.object_id
    assert notes[ 1 ][ 1 ] == self.note.title

  def test_all_notes_without_login( self ):
    result = self.http_post( "/notebooks/all_notes/", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result.get( "error" )

  def test_export_html( self ):
    self.login()

    note3 = Note.create( "55", u"<h3>blah</h3>foo", notebook_id = self.notebook.object_id )
    self.database.save( note3 )

    result = self.http_get(
      "/notebooks/export_html/%s" % self.notebook.object_id,
      session_id = self.session_id,
    )
    assert result.get( "notebook_name" ) == self.notebook.name

    notes = result.get( "notes" )
    assert len( notes ) == self.database.select_one( int, self.notebook.sql_count_notes() )
    startup_note_allowed = True
    previous_revision = None

    # assert that startup notes come first, then normal notes in descending revision order
    for note in notes:
      if note.startup:
        assert startup_note_allowed
      else:
        startup_note_allowed = False

        if previous_revision:
          assert note.revision < previous_revision

        previous_revision = note.revision

      db_note = self.database.load( Note, note.object_id )
      assert db_note
      assert note.object_id == db_note.object_id
      assert note.revision == db_note.revision
      assert note.title == db_note.title
      assert note.contents == db_note.contents
      assert note.notebook_id == db_note.notebook_id
      assert note.startup == db_note.startup
      assert note.deleted_from_id == db_note.deleted_from_id
      assert note.rank == db_note.rank
      assert note.user_id == db_note.user_id
      assert note.creation == db_note.creation
 
  def test_export_html_without_login( self ):
    note3 = Note.create( "55", u"<h3>blah</h3>foo", notebook_id = self.notebook.object_id )
    self.database.save( note3 )

    path = "/notebooks/export_html/%s" % self.notebook.object_id
    result = self.http_get(
      path,
      session_id = self.session_id,
    )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )
      
  def test_export_html_with_unknown_notebook( self ):
    self.login()

    result = self.http_get(
      "/notebooks/export_html/%s" % self.unknown_notebook_id,
      session_id = self.session_id,
    )

    assert result.get( "error" )

  def test_export_csv( self, note_text = None ):
    self.login()

    if not note_text:
      note_text = u"foo"

    note3 = Note.create( "55", u"<h3>blah</h3>%s" % note_text, notebook_id = self.notebook.object_id )
    self.database.save( note3 )

    result = self.http_get(
      "/notebooks/export_csv/%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == u"text/csv;charset=utf-8"
    assert headers[ u"Content-Disposition" ] == 'attachment; filename=wiki.csv'

    gen = result[ u"body" ]
    assert isinstance( gen, types.GeneratorType )
    pieces = []

    try:
      for piece in gen:
        pieces.append( piece )
    except AttributeError, exc:
      if u"session_storage" not in str( exc ):
        raise exc

    csv_data = "".join( pieces )
    reader = csv.reader( StringIO( csv_data ) )

    row = reader.next()
    expected_header = [ u"contents", u"title", u"note_id", u"startup", u"username", u"revision_date" ]
    assert row == expected_header

    expected_note_count = self.database.select_one( int, self.notebook.sql_count_notes() )
    note_count = 0
    startup_note_allowed = True
    previous_revision = None

    # assert that startup notes come first, then normal notes in descending revision order
    for row in reader:
      note_count += 1

      assert len( row ) == len( expected_header )
      ( contents, title, note_id, startup, username, revision_date ) = row
      
      if startup:
        assert startup_note_allowed
      else:
        startup_note_allowed = False

        if previous_revision:
          assert revision_date < previous_revision

        previous_revision = revision_date

      db_note = self.database.load( Note, note_id )
      assert db_note
      assert contents.decode( "utf8" ) == db_note.contents
      assert title.decode( "utf8" ) == db_note.title
      assert note_id.decode( "utf8" ) == db_note.object_id
      assert startup.decode( "utf8" ) == db_note.startup and u"1" or "0"
      assert username.decode( "utf8" ) == ( db_note.user_id and self.user.username or u"" )
      assert revision_date.decode( "utf8" ) == unicode( db_note.revision )

    assert note_count == expected_note_count

  def test_export_csv_with_unicode( self ):
    self.test_export_csv( note_text = u"ümlaut.png" )
 
  def test_export_csv_without_login( self ):
    note3 = Note.create( "55", u"<h3>blah</h3>foo", notebook_id = self.notebook.object_id )
    self.database.save( note3 )

    path = "/notebooks/export_csv/%s" % self.notebook.object_id
    result = self.http_get(
      path,
      session_id = self.session_id,
    )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )
      
  def test_export_csv_with_unknown_notebook( self ):
    self.login()

    result = self.http_get(
      "/notebooks/export_csv/%s" % self.unknown_notebook_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ u"body" ][ 0 ]

  def test_create( self ):
    self.login()

    result = self.http_post( "/notebooks/create", dict(), session_id = self.session_id )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

    new_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ].split( u"?" )[ 0 ]
    notebook = self.database.load( Notebook, new_notebook_id )

    assert isinstance( notebook, Notebook )
    assert notebook.object_id == new_notebook_id
    assert notebook.name == u"new notebook"
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.trash_id

    self.user.sql_load_notebooks()
    notebooks = self.database.select_many( Notebook, self.user.sql_load_notebooks() )
    new_notebook = [ notebook for notebook in notebooks if notebook.object_id == new_notebook_id ][ 0 ]
    assert new_notebook.rank == 1

  def test_contents_after_create( self ):
    self.login()

    result = self.http_post( "/notebooks/create", dict(), session_id = self.session_id )
    new_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ].split( u"?" )[ 0 ]

    result = cherrypy.root.notebooks.contents(
      notebook_id = new_notebook_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    assert result[ "total_notes_count" ] == 0
    assert result[ "startup_notes" ] == []
    assert result[ "notes" ] == []
    assert result[ "invites" ] == []

    assert notebook.object_id == new_notebook_id
    assert notebook.read_write == True
    assert notebook.owner == True

  def test_create_without_login( self ):
    result = self.http_post( "/notebooks/create", dict() )

    assert result[ u"error" ]

  def test_rename( self ):
    self.login()

    new_name = u"renamed notebook"
    result = self.http_post( "/notebooks/rename", dict(
      notebook_id = self.notebook.object_id,
      name = new_name,
    ), session_id = self.session_id )

    assert u"error" not in result

  def test_contents_after_rename( self ):
    self.login()

    new_name = u"renamed notebook"
    self.http_post( "/notebooks/rename", dict(
      notebook_id = self.notebook.object_id,
      name = new_name,
    ), session_id = self.session_id )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    assert notebook.name == new_name
    assert notebook.user_id == self.user.object_id

  def test_rename_without_login( self ):
    new_name = u"renamed notebook"
    result = self.http_post( "/notebooks/rename", dict(
      notebook_id = self.notebook.object_id,
      name = new_name,
    ) )

    assert result[ u"error" ]

  def test_rename_trash( self ):
    self.login()

    new_name = u"renamed notebook"
    result = self.http_post( "/notebooks/rename", dict(
      notebook_id = self.notebook.trash_id,
      name = new_name,
    ), session_id = self.session_id )

    assert u"error" in result

  def test_rename_with_reserved_luminotes_name( self ):
    self.login()

    new_name = u"Luminotes blog"
    result = self.http_post( "/notebooks/rename", dict(
      notebook_id = self.notebook.object_id,
      name = new_name,
    ), session_id = self.session_id )

    assert result[ u"error" ]

  def test_rename_with_reserved_trash_name( self ):
    self.login()

    new_name = u" trash  "
    result = self.http_post( "/notebooks/rename", dict(
      notebook_id = self.notebook.object_id,
      name = new_name,
    ), session_id = self.session_id )

    assert result[ u"error" ]

  def test_delete( self ):
    self.login()

    result = self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

    # assert that we're redirected to a newly created notebook
    remaining_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ].split( u"?" )[ 0 ]
    notebook = self.database.load( Notebook, remaining_notebook_id )

    assert isinstance( notebook, Notebook )
    assert notebook.object_id == remaining_notebook_id
    assert notebook.name == u"my notebook"
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.trash_id
    assert notebook.user_id == self.user.object_id

  def test_delete_with_remaining_notebook( self ):
    # create a second notebook, which we should be redirected to after the first notebook is deleted
    trash = Notebook.create( self.database.next_id( Notebook ), u"trash" )
    self.database.save( trash, commit = False )
    notebook = Notebook.create( self.database.next_id( Notebook ), u"notebook", trash.object_id )
    self.database.save( notebook, commit = False )
    self.database.execute( self.user.sql_save_notebook( notebook.object_id, read_write = True, owner = True, rank = 1 ) )
    self.database.execute( self.user.sql_save_notebook( notebook.trash_id, read_write = True, owner = True, rank = 1 ) )
    self.database.commit()

    self.login()

    result = self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

    # assert that we're redirected to the second notebook
    remaining_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ].split( u"?" )[ 0 ]
    assert remaining_notebook_id
    assert remaining_notebook_id == notebook.object_id

  def test_delete_with_remaining_read_only_notebook( self ):
    # create a second read-only notebook, which we should NOT be redirected to after the first
    # notebook is deleted
    trash = Notebook.create( self.database.next_id( Notebook ), u"trash" )
    self.database.save( trash, commit = False )
    notebook = Notebook.create( self.database.next_id( Notebook ), u"notebook", trash.object_id )
    self.database.save( notebook, commit = False )
    self.database.execute( self.user.sql_save_notebook( notebook.object_id, read_write = False, owner = False, rank = 1 ) )
    self.database.execute( self.user.sql_save_notebook( notebook.trash_id, read_write = False, owner = False, rank = 1 ) )
    self.database.commit()

    self.login()

    result = self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

    # assert that we're redirected to a newly created notebook
    remaining_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ].split( u"?" )[ 0 ]
    notebook = self.database.load( Notebook, remaining_notebook_id )

    assert isinstance( notebook, Notebook )
    assert notebook.object_id == remaining_notebook_id
    assert notebook.name == u"my notebook"
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.trash_id
    assert notebook.user_id == self.user.object_id

  def test_contents_after_delete( self ):
    self.login()

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    assert notebook.deleted == True
    assert notebook.user_id == self.user.object_id

  def test_contents_after_delete_twice( self ):
    self.login()

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    assert notebook.deleted == True
    assert notebook.user_id == self.user.object_id

  def test_delete_without_login( self ):
    result = self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"error" ]

  def test_delete_trash( self ):
    self.login()

    result = self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.trash_id,
    ), session_id = self.session_id )

    assert u"error" in result

  def test_delete_forever( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_forever", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert u"error" not in result

  @raises( Access_error )
  def test_contents_after_delete_forever( self ):
    self.login()

    self.http_post( "/notebooks/delete_forever", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

  def test_delete_then_delete_forever( self ):
    self.login()

    result = self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/delete_forever", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert u"error" not in result

  @raises( Access_error )
  def test_contents_after_delete_then_delete_forever( self ):
    self.login()

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    self.http_post( "/notebooks/delete_forever", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

  def test_delete_forever_without_login( self ):
    result = self.http_post( "/notebooks/delete_forever", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"error" ]

  def test_delete_forever_trash( self ):
    self.login()

    result = self.http_post( "/notebooks/delete_forever", dict(
      notebook_id = self.notebook.trash_id,
    ), session_id = self.session_id )

    assert u"error" in result

  def test_undelete( self ):
    self.login()

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/undelete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

    # assert that we're redirected to the undeleted notebook
    notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]
    notebook = self.database.load( Notebook, notebook_id )

    assert isinstance( notebook, Notebook )
    assert notebook.object_id == notebook_id
    assert notebook.name == self.notebook.name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.trash_id
    assert notebook.user_id == self.user.object_id

  def test_contents_after_undelete( self ):
    self.login()

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/undelete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = cherrypy.root.notebooks.contents(
      notebook_id = self.notebook.object_id,
      user_id = self.user.object_id,
    )

    notebook = result[ "notebook" ]
    assert notebook.deleted == False
    assert notebook.user_id == self.user.object_id

  def test_undelete_without_login( self ):
    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/undelete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"error" ]

  def test_undelete_twice( self ):
    self.login()

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    self.http_post( "/notebooks/undelete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/undelete", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

    # assert that we're redirected to the undeleted notebook
    notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]
    notebook = self.database.load( Notebook, notebook_id )

    assert isinstance( notebook, Notebook )
    assert notebook.object_id == notebook_id
    assert notebook.name == self.notebook.name
    assert notebook.read_write == True
    assert notebook.owner == True
    assert notebook.trash_id
    assert notebook.user_id == self.user.object_id

  def test_move_up( self ):
    self.login()
    self.make_extra_notebooks()

    result = self.http_post( "/notebooks/move_up", dict(
      notebook_id = self.notebook2.object_id,
    ), session_id = self.session_id )

    assert u"error" not in result

    notebooks = self.database.select_many( Notebook, self.user.sql_load_notebooks( parents_only = True, undeleted_only = True ) )

    assert notebooks
    assert len( notebooks ) == 3
    assert notebooks[ 0 ].object_id == self.notebook2.object_id
    assert notebooks[ 0 ].rank == 0
    assert notebooks[ 1 ].object_id == self.notebook.object_id
    assert notebooks[ 1 ].rank == 1
    assert notebooks[ 2 ].object_id == self.notebook3.object_id
    assert notebooks[ 2 ].rank == 2

  def test_move_up_and_wrap( self ):
    self.login()
    self.make_extra_notebooks()

    result = self.http_post( "/notebooks/move_up", dict(
      notebook_id = self.notebook.object_id,
    ), session_id = self.session_id )

    assert u"error" not in result

    notebooks = self.database.select_many( Notebook, self.user.sql_load_notebooks( parents_only = True, undeleted_only = True ) )

    assert notebooks
    assert len( notebooks ) == 3
    assert notebooks[ 0 ].object_id == self.notebook2.object_id
    assert notebooks[ 0 ].rank == 1
    assert notebooks[ 1 ].object_id == self.notebook3.object_id
    assert notebooks[ 1 ].rank == 2
    assert notebooks[ 2 ].object_id == self.notebook.object_id
    assert notebooks[ 2 ].rank == 3

  def test_move_up_without_login( self ):
    self.make_extra_notebooks()

    result = self.http_post( "/notebooks/move_up", dict(
      notebook_id = self.notebook2.object_id,
    ) )

    assert u"access" in result[ u"error" ]

  def test_move_up_without_access( self ):
    self.login2()
    self.make_extra_notebooks()

    result = self.http_post( "/notebooks/move_up", dict(
      notebook_id = self.notebook2.object_id,
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]

  def test_move_up_trash( self ):
    self.login()
    self.make_extra_notebooks()

    result = self.http_post( "/notebooks/move_up", dict(
      notebook_id = self.trash.object_id,
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]

  def test_move_up_deleted_notebook( self ):
    self.login()
    self.make_extra_notebooks()

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook2.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/move_up", dict(
      notebook_id = self.notebook2.object_id,
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]

  def test_move_down( self ):
    self.login()
    self.make_extra_notebooks()

    result = self.http_post( "/notebooks/move_down", dict(
      notebook_id = self.notebook2.object_id,
    ), session_id = self.session_id )

    assert u"error" not in result

    notebooks = self.database.select_many( Notebook, self.user.sql_load_notebooks( parents_only = True, undeleted_only = True ) )

    assert notebooks
    assert len( notebooks ) == 3
    assert notebooks[ 0 ].object_id == self.notebook.object_id
    assert notebooks[ 0 ].rank == 0
    assert notebooks[ 1 ].object_id == self.notebook3.object_id
    assert notebooks[ 1 ].rank == 1
    assert notebooks[ 2 ].object_id == self.notebook2.object_id
    assert notebooks[ 2 ].rank == 2

  def test_move_down_and_wrap( self ):
    self.login()
    self.make_extra_notebooks()

    result = self.http_post( "/notebooks/move_down", dict(
      notebook_id = self.notebook3.object_id,
    ), session_id = self.session_id )

    assert u"error" not in result

    notebooks = self.database.select_many( Notebook, self.user.sql_load_notebooks( parents_only = True, undeleted_only = True ) )

    assert notebooks
    assert len( notebooks ) == 3
    assert notebooks[ 0 ].object_id == self.notebook3.object_id
    assert notebooks[ 0 ].rank == -1
    assert notebooks[ 1 ].object_id == self.notebook.object_id
    assert notebooks[ 1 ].rank == 0
    assert notebooks[ 2 ].object_id == self.notebook2.object_id
    assert notebooks[ 2 ].rank == 1

  def test_move_down_without_login( self ):
    self.make_extra_notebooks()

    result = self.http_post( "/notebooks/move_down", dict(
      notebook_id = self.notebook2.object_id,
    ) )

    assert u"access" in result[ u"error" ]

  def test_move_down_without_access( self ):
    self.login2()
    self.make_extra_notebooks()

    result = self.http_post( "/notebooks/move_down", dict(
      notebook_id = self.notebook2.object_id,
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]

  def test_move_down_trash( self ):
    self.login()
    self.make_extra_notebooks()

    result = self.http_post( "/notebooks/move_down", dict(
      notebook_id = self.trash.object_id,
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]

  def test_move_down_deleted_notebook( self ):
    self.login()
    self.make_extra_notebooks()

    self.http_post( "/notebooks/delete", dict(
      notebook_id = self.notebook2.object_id,
    ), session_id = self.session_id )

    result = self.http_post( "/notebooks/move_down", dict(
      notebook_id = self.notebook2.object_id,
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]

  def test_recent_notes( self ):
    result = cherrypy.root.notebooks.recent_notes(
      self.notebook.object_id,
      user_id = self.user.object_id,
    )

    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2

    notes = result.get( u"notes" )
    assert notes
    assert len( notes ) == 2
    assert notes[ 0 ].object_id == self.note2.object_id
    assert notes[ 1 ].object_id == self.note.object_id

    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert result.get( u"start" ) == 0
    assert result.get( u"count" ) == 10

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_recent_notes_with_start( self ):
    result = cherrypy.root.notebooks.recent_notes(
      self.notebook.object_id,
      start = 1,
      user_id = self.user.object_id,
    )

    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2

    notes = result.get( u"notes" )
    assert notes
    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note.object_id

    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert result.get( u"start" ) == 1
    assert result.get( u"count" ) == 10

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  def test_recent_notes_with_count( self ):
    result = cherrypy.root.notebooks.recent_notes(
      self.notebook.object_id,
      count = 1,
      user_id = self.user.object_id,
    )

    assert result.get( u"user" ).object_id == self.user.object_id
    assert len( result.get( u"notebooks" ) ) == 3
    assert result.get( u"login_url" ) is None
    assert result.get( u"logout_url" )
    assert result.get( u"rate_plan" )
    assert result.get( u"notebook" ).object_id == self.notebook.object_id
    assert len( result.get( u"startup_notes" ) ) == 1
    assert result[ "total_notes_count" ] == 2

    notes = result.get( u"notes" )
    assert notes
    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note2.object_id

    assert result.get( u"parent_id" ) == None
    assert result.get( u"note_read_write" ) in ( None, True )
    assert result.get( u"start" ) == 0
    assert result.get( u"count" ) == 1

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == 0

  @raises( Access_error )
  def test_recent_notes_with_unknown_notebok( self ):
    result = cherrypy.root.notebooks.recent_notes(
      self.unknown_notebook_id,
      user_id = self.user.object_id,
    )

  @raises( Access_error )
  def test_recent_notes_with_incorrect_user( self ):
    result = cherrypy.root.notebooks.recent_notes(
      self.notebook.object_id,
      user_id = self.anonymous.object_id,
    )

  def test_load_recent_updates( self ):
    self.login()

    result = self.http_get(
      "/notebooks/load_recent_updates?%s" % urllib.urlencode( [
        ( "notebook_id", self.notebook.object_id ),
        ( "start", "0" ),
        ( "count", "10" ),
      ] ),
      session_id = self.session_id,
    )

    notes = result.get( u"notes" )
    assert notes
    assert len( notes ) == 2
    assert notes[ 0 ].object_id == self.note2.object_id
    assert notes[ 1 ].object_id == self.note.object_id

  def test_load_recent_updates_with_non_default_start( self ):
    self.login()

    result = self.http_get(
      "/notebooks/load_recent_updates?%s" % urllib.urlencode( [
        ( "notebook_id", self.notebook.object_id ),
        ( "start", "1" ),
        ( "count", "10" ),
      ] ),
      session_id = self.session_id,
    )

    notes = result.get( u"notes" )
    assert notes
    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note.object_id

  def test_load_recent_updates_with_too_small_start( self ):
    self.login()

    result = self.http_get(
      "/notebooks/load_recent_updates?%s" % urllib.urlencode( [
        ( "notebook_id", self.notebook.object_id ),
        ( "start", "-1" ),
        ( "count", "10" ),
      ] ),
      session_id = self.session_id,
    )

    assert u"too small" in result[ "error" ]

  def test_load_recent_updates_with_non_default_count( self ):
    self.login()

    result = self.http_get(
      "/notebooks/load_recent_updates?%s" % urllib.urlencode( [
        ( "notebook_id", self.notebook.object_id ),
        ( "start", "0" ),
        ( "count", "1" ),
      ] ),
      session_id = self.session_id,
    )

    notes = result.get( u"notes" )
    assert notes
    assert len( notes ) == 1
    assert notes[ 0 ].object_id == self.note2.object_id

  def test_load_recent_updates_with_too_small_count( self ):
    self.login()

    result = self.http_get(
      "/notebooks/load_recent_updates?%s" % urllib.urlencode( [
        ( "notebook_id", self.notebook.object_id ),
        ( "start", "0" ),
        ( "count", "0" ),
      ] ),
      session_id = self.session_id,
    )

    assert u"too small" in result[ "error" ]

  def test_load_recent_updates_without_login( self ):
    path = "/notebooks/load_recent_updates?%s" % urllib.urlencode( [
      ( "notebook_id", self.notebook.object_id ),
      ( "start", "0" ),
      ( "count", "10" ),
    ] )

    result = self.http_get( path )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def test_load_recent_updates_without_access( self ):
    self.login2()
    self.make_extra_notebooks()

    result = self.http_get(
      "/notebooks/load_recent_updates?%s" % urllib.urlencode( [
        ( "notebook_id", self.notebook2.object_id ),
        ( "start", "0" ),
        ( "count", "10" ),
      ] ),
      session_id = self.session_id,
    )

    assert u"access" in result[ "error" ]

  def test_load_recent_updates_with_unknown_notebook( self ):
    self.login()

    result = self.http_get(
      "/notebooks/load_recent_updates?%s" % urllib.urlencode( [
        ( "notebook_id", self.unknown_notebook_id ),
        ( "start", "0" ),
        ( "count", "10" ),
      ] ),
      session_id = self.session_id,
    )

    assert u"access" in result[ "error" ]

  def test_import_csv( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5'
    expected_notes = [
      ( "blah and stuff", "3.3" ), # ( title, contents )
      ( "whee", "hmm\nfoo" ),
      ( "4", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result )

  LINK_PATTERN = re.compile( '<a href="([^"]*)"\s*([^>]*)>([^<]*)</a>', re.IGNORECASE )
  NOTE_URL_PATTERN = re.compile( '([^"]*)/notebooks/(\w+)\?note_id=(\w+)', re.IGNORECASE )

  def __assert_imported_notebook( self, expected_notes, result, plaintext = True ):
    assert result[ u"redirect" ].startswith( u"/notebooks/" )

    # make sure that a notebook has been created with the imported notes
    new_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ].split( u"?" )[ 0 ]
    notebook = self.database.load( Notebook, new_notebook_id )

    assert notebook.name == u"imported notebook"
    assert notebook.trash_id
    assert notebook.read_write is True
    assert notebook.owner is True
    assert notebook.deleted is False
    assert notebook.user_id == self.user.object_id
    assert notebook.rank is None

    result = self.http_get(
      "/notebooks/%s" % notebook.object_id,
      session_id = self.session_id,
    )

    recent_notes = result.get( "recent_notes" )
    assert recent_notes
    assert len( recent_notes ) == len( expected_notes )

    # reverse the recent notes because they're in reverse chronological order
    recent_notes.reverse()

    for ( note, ( title, contents ) ) in zip( recent_notes, expected_notes ):
      assert note.title == title
      if plaintext is True:
        contents = contents.replace( u"\n", u"<br />" )
      if plaintext is True or u"<h3>" not in contents:
        contents = u"<h3>%s</h3>%s" % ( title, contents )
      if plaintext is False:
        link_match = self.LINK_PATTERN.search( contents )

        # if there's a link, make sure it is a rewritten note link or has a link target
        if link_match:
          ( url, attributes, title ) = link_match.groups()

          url_match = self.NOTE_URL_PATTERN.search( url )
          if url_match:
            imported_notebook = self.database.select_one( Notebook, "select * from notebook where name = 'imported notebook' limit 1;" )
            ( protocol_and_host, notebook_id, note_id ) = url_match.groups()
            assert attributes == u""
            assert protocol_and_host == u""

            # assert that the link has been rewritten to point to a note in the new notebook
            assert note_id
            rewritten_note = self.database.load( Note, note_id )
            if rewritten_note:
              assert rewritten_note.notebook_id == imported_notebook.object_id
              assert notebook_id == imported_notebook.object_id
            else:
              assert notebook_id == self.notebook.object_id
          else:
            assert attributes.startswith( u'target="' )

      assert note.contents == contents

    # make sure the CSV data file has been deleted from the database and filesystem
    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > 0

  def test_import_csv_title_already_in_contents( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff","<h3>yay</h3>3.3"\n"8","whee","hmm\n<h3>my title</h3>foo"\n3,4,5'
    expected_notes = [
      ( "yay", "<h3>yay</h3>3.3" ), # ( title, contents )
      ( "my title", "hmm\n<h3>my title</h3>foo" ),
      ( "4", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = False,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result, plaintext = False )

  def test_import_csv_title_already_in_plaintext_contents( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff","hi\n<h3>yay</h3>3.3"\n"8","whee","hmm\n<h3>my title</h3>foo"\n3,4,5'
    expected_notes = [
      ( "blah and stuff", "hi<br />&lt;h3&gt;yay&lt;/h3&gt;3.3" ), # ( title, contents )
      ( "whee", "hmm<br />&lt;h3&gt;my title&lt;/h3&gt;foo" ),
      ( "4", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result, plaintext = True )

  def test_import_csv_unknown_file_id( self ):
    self.login()

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = u"unknownfileid",
      content_column = 2,
      title_column = 1,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]

  def test_import_csv_content_column_too_high( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5'

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 5,
      title_column = 1,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    assert u"import" in result[ u"error" ]

  def test_import_csv_title_column_too_high( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5'

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 5,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    assert u"import" in result[ u"error" ]

  def test_import_csv_same_title_and_content_columns( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5'
    expected_notes = [
      ( "3.3", "3.3" ), # ( title, contents )
      ( "hmm", "hmm\nfoo" ),
      ( "5", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 2,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result )

  def test_import_csv_html_title( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah <i>and</i>&nbsp; stuff<br />",3.3\n"8","whee<p>","hmm\nfoo"\n3,4,5'
    expected_notes = [
      ( "blah &lt;i&gt;and&lt;/i&gt;&amp;nbsp; stuff&lt;br /&gt;", "3.3" ), # ( title, contents )
      ( "whee&lt;p&gt;", "hmm\nfoo" ),
      ( "4", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result )

  def test_import_csv_no_title_column( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5'
    expected_notes = [
      ( "3.3", "3.3" ), # ( title, contents )
      ( "hmm", "hmm\nfoo" ),
      ( "5", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = None,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result )

  def test_import_csv_no_title_column_and_title_already_in_contents( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff","<h3>yay</h3>3.3"\n"8","whee","hmm\n<h3>my title</h3>foo"\n3,4,5'
    expected_notes = [
      ( "yay", "<h3>yay</h3>3.3" ), # ( title, contents )
      ( "my title", "hmm\n<h3>my title</h3>foo" ),
      ( "5", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = None,
      plaintext = False,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result, plaintext = False )

  def test_import_csv_no_title_column_and_title_already_in_plaintext_contents( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff","hi\n<h3>yay</h3>3.3"\n"8","whee","hmm\n<h3>my title</h3>foo"\n3,4,5'
    expected_notes = [
      ( "hi", "hi<br />&lt;h3&gt;yay&lt;/h3&gt;3.3" ), # ( title, contents )
      ( "hmm", "hmm<br />&lt;h3&gt;my title&lt;/h3&gt;foo" ),
      ( "5", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = None,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result, plaintext = True )

  def test_import_csv_no_title_column_and_html_first_line( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff","3 < 4<img>"\n"8","whee","<b>hmm</b>\nfoo"\n3,4,5'
    expected_notes = [
      ( "3 &lt; 4&lt;img&gt;", "3 &lt; 4&lt;img&gt;" ), # ( title, contents )
      ( "&lt;b&gt;hmm&lt;/b&gt;", "&lt;b&gt;hmm&lt;/b&gt;\nfoo" ),
      ( "5", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = None,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result )

  def test_import_csv_no_title_column_and_long_first_line( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff","Ten percent of nuthin\' is...let me do the math here...nuthin\' into nuthin\'...carry the nuthin\'..."\n"8","whee","I brought you some supper but if you\'d prefer a lecture, I\'ve a few very catchy ones prepped...sin and hellfire... one has lepers.\n--Book"\n3,4,5'

    # expect the long titles to be truncated on a word boundary
    expected_notes = [
      ( "Ten percent of nuthin' is...let me do the math here...nuthin' into", "Ten percent of nuthin' is...let me do the math here...nuthin' into nuthin'...carry the nuthin'..." ),
      ( "I brought you some supper but if you'd prefer a lecture, I've a few very catchy", "I brought you some supper but if you'd prefer a lecture, I've a few very catchy ones prepped...sin and hellfire... one has lepers.\n--Book" ),
      ( "5", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = None,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result )

  def test_import_csv_no_title_column_and_long_first_line_without_spaces( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff","abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz"\n"8","whee","ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZ\nfoo"\n3,4,5'

    # expect the long titles not to be truncated since there are no spaces
    expected_notes = [
      ( "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz", "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz" ),
      ( "ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZ", "ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZ\nfoo" ),
      ( "5", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = None,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result )

  def test_import_csv_no_title_column_and_blank_first_line( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff","\n\n3.3"\n"8","whee","\nfoo"\n3,4,5'
    expected_notes = [
      ( "3.3", "3.3" ), # ( title, contents )
      ( "foo", "foo" ),
      ( "5", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = None,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result )

  def test_import_csv_no_title_column_and_empty_contents( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff","\n\n\n  \n"\n"8","whee","foo"\n3,4,5'
    expected_notes = [
      ( "foo", "foo" ),
      ( "5", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = None,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result )

  def test_import_csv_plaintext_content_as_html( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5'
    expected_notes = [
      ( "blah and stuff", "3.3" ), # ( title, contents )
      ( "whee", "hmm\nfoo" ),
      ( "4", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = False,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result, plaintext = False )

  def test_import_csv_html_title( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"<i>blah</i> and stuff",3.3\n"8","wh&nbsp;ee","hmm\nfoo"\n3,4,5'
    expected_notes = [
      ( "blah and stuff", "3.3" ), # ( title, contents )
      ( "wh&nbsp;ee", "hmm\nfoo" ),
      ( "4", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = False,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result, plaintext = False )

  def test_import_csv_html_content( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff","3.<b>3 &nbsp;</b>"\n"8","whee","hmm\n<i>foo</i>"\n3,4,5'
    expected_notes = [
      ( "blah and stuff", "3.<b>3 &nbsp;</b>" ), # ( title, contents )
      ( "whee", "hmm\n<i>foo</i>" ),
      ( "4", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = False,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result, plaintext = False )

  def test_import_csv_html_content_without_title( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff","3.<b>3 &nbsp;</b>"\n"8","whee","hmm\n<i>foo</i>"\n3,4,5'
    expected_notes = [
      ( "3.3 &nbsp;", "3.<b>3 &nbsp;</b>" ), # ( title, contents )
      ( "hmm", "hmm\n<i>foo</i>" ),
      ( "5", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = None,
      plaintext = False,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result, plaintext = False )

  def test_import_csv_html_content_with_link( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff","3.<b>3 &nbsp;</b>"\n"8","whee","hmm\n<a href=""http://luminotes.com/"">foo</a>"\n3,4,5'
    expected_notes = [
      ( "blah and stuff", "3.<b>3 &nbsp;</b>" ), # ( title, contents )
      ( "whee", 'hmm\n<a href="http://luminotes.com/" target="_new">foo</a>' ),
      ( "4", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = False,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result, plaintext = False )

  def test_import_csv_html_content_with_link_and_target( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff","3.<b>3 &nbsp;</b>"\n"8","whee","hmm\n<a href=""http://luminotes.com/"" target=""something"">foo</a>"\n3,4,5'
    expected_notes = [
      ( "blah and stuff", "3.<b>3 &nbsp;</b>" ), # ( title, contents )
      ( "whee", 'hmm\n<a href="http://luminotes.com/" target="something">foo</a>' ),
      ( "4", "5" ),
    ]

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = False,
      import_button = u"import",
    ), session_id = self.session_id )

    self.__assert_imported_notebook( expected_notes, result, plaintext = False )

  def test_import_csv_html_content_with_internal_note_link( self ):
    self.login()

    # one of the imported notes contains a link to one of the other imported notes
    note_url = "/notebooks/%s?note_id=%s" % ( self.notebook.object_id, "idthree" )
    csv_data = '"label 1","label 2","label 3","note_id",\n5,"blah and stuff","3.<b>3 &nbsp;</b>",idone\n"8","whee","hmm\n<a href=""%s"">foo</a>",idtwo\n3,4,5,idthree' % note_url

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = False,
      import_button = u"import",
    ), session_id = self.session_id )

    notebook = self.database.select_one( Notebook, "select * from notebook where name = 'imported notebook' limit 1;" )
    note = self.database.select_one( Note, notebook.sql_load_note_by_title( u"4" ) )

    rewritten_note_url = "/notebooks/%s?note_id=%s" % ( notebook.object_id, note.object_id )
    expected_notes = [
      ( "blah and stuff", "3.<b>3 &nbsp;</b>" ), # ( title, contents )
      ( "4", "5" ),
      ( "whee", 'hmm\n<a href="%s">foo</a>' % rewritten_note_url ),
    ]

    self.__assert_imported_notebook( expected_notes, result, plaintext = False )

  def test_import_csv_html_content_with_internal_note_link_and_blank_note_id_value( self ):
    self.login()

    # one of the imported notes contains a link to one of the other imported notes
    note_url = "/notebooks/%s?note_id=%s" % ( self.notebook.object_id, "idthree" )
    csv_data = '"label 1","label 2","label 3","note_id",\n5,"blah and stuff","3.<b>3 &nbsp;</b>",\n"8","whee","hmm\n<a href=""%s"">foo</a>",idtwo\n3,4,5,idthree' % note_url

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = False,
      import_button = u"import",
    ), session_id = self.session_id )

    notebook = self.database.select_one( Notebook, "select * from notebook where name = 'imported notebook' limit 1;" )
    note = self.database.select_one( Note, notebook.sql_load_note_by_title( u"4" ) )

    rewritten_note_url = "/notebooks/%s?note_id=%s" % ( notebook.object_id, note.object_id )
    expected_notes = [
      ( "blah and stuff", "3.<b>3 &nbsp;</b>" ), # ( title, contents )
      ( "4", "5" ),
      ( "whee", 'hmm\n<a href="%s">foo</a>' % rewritten_note_url ),
    ]

    self.__assert_imported_notebook( expected_notes, result, plaintext = False )

  def test_import_csv_html_content_with_internal_note_link_to_unknown_note( self ):
    self.login()

    # one of the imported notes contains a link to one of the other imported notes
    note_url = "/notebooks/%s?note_id=%s" % ( self.notebook.object_id, "idunknown" )
    csv_data = '"label 1","label 2","label 3","note_id",\n5,"blah and stuff","3.<b>3 &nbsp;</b>",idone\n"8","whee","hmm\n<a href=""%s"">foo</a>",idtwo\n3,4,5,idthree' % note_url

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = False,
      import_button = u"import",
    ), session_id = self.session_id )

    expected_notes = [
      ( "blah and stuff", "3.<b>3 &nbsp;</b>" ), # ( title, contents )
      ( "4", "5" ),
      ( "whee", 'hmm\n<a href="%s">foo</a>' % note_url ), # the note url should not be rewritten
    ]

    self.__assert_imported_notebook( expected_notes, result, plaintext = False )

  def test_import_csv_html_content_with_internal_note_link_without_note_id_column( self ):
    self.login()

    # one of the imported notes contains a link to one of the other imported notes
    note_url = "/notebooks/%s?note_id=%s" % ( self.notebook.object_id, "idthree" )
    csv_data = '"label 1","label 2","label 3",\n5,"blah and stuff","3.<b>3 &nbsp;</b>"\n"8","whee","hmm\n<a href=""%s"">foo</a>"\n3,4,5' % note_url

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = False,
      import_button = u"import",
    ), session_id = self.session_id )

    expected_notes = [
      ( "blah and stuff", "3.<b>3 &nbsp;</b>" ), # ( title, contents )
      ( "whee", 'hmm\n<a href="%s">foo</a>' % note_url ), # the note url should not be rewritten
      ( "4", "5" ),
    ]

    self.__assert_imported_notebook( expected_notes, result, plaintext = False )

  def test_import_csv_without_login( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5'

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = True,
      import_button = u"import",
    ) )

    assert u"access" in result[ u"error" ]

  def test_import_csv_without_access( self ):
    self.login()
    self.make_extra_notebooks()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5'

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook2.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.login2()

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    assert u"access" in result[ u"error" ]

  def test_import_csv_invalid( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",,,,,,3.3\n"8","whee","hmm\nfoo"\n3,4,5'

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post( "/notebooks/import_csv/", dict(
      file_id = self.file_id,
      content_column = 2,
      title_column = 1,
      plaintext = True,
      import_button = u"import",
    ), session_id = self.session_id )

    assert result[ u"error" ]

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
