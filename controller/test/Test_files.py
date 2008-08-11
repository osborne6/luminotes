# -*- coding: utf8 -*-

import time
import types
import urllib
import cherrypy
from nose.tools import raises
from threading import Thread
from StringIO import StringIO
from PIL import Image
from Test_controller import Test_controller
from model.Notebook import Notebook
from model.Note import Note
from model.User import User
from model.Invite import Invite
from model.File import File
from controller.Notebooks import Access_error
from controller.Files import Upload_file, Parse_error


class Test_files( Test_controller ):
  def setUp( self ):
    Test_controller.setUp( self )

    self.notebook = None
    self.anon_notebook = None
    self.username = u"mulder"
    self.password = u"trustno1"
    self.email_address = u"outthere@example.com"
    self.username2 = u"deepthroat"
    self.password2 = u"mmmtobacco"
    self.email_address2 = u"parkinglot@example.com"
    self.user = None
    self.user2 = None
    self.anonymous = None
    self.session_id = None
    self.file_id = "22"
    self.filename = "file.png"
    self.unicode_filename = u"ümlaut.png"
    self.new_filename = "newfile.png"
    self.file_data = "foobar\x07`-=[]\;',./ ~!@#$%^&*()_+{}|:\"<>?" * 100
    self.weird_filename = self.file_data + ".png"
    self.content_type = "image/png"
    self.upload_thread = None

    # make Upload_file deal in fake files rather than actually using the filesystem
    Upload_file.fake_files = {} # map of file_id to fake file object

    @staticmethod
    def open_file( file_id, mode = None ):
      fake_file = Upload_file.fake_files.get( file_id )

      if fake_file:
        return fake_file

      if mode not in ( "w", "w+" ):
        raise IOError()

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

    self.anon_notebook = Notebook.create( self.database.next_id( Notebook ), u"anon_notebook", user_id = user_id )
    self.database.save( self.anon_notebook, commit = False )

    self.database.execute( self.user.sql_save_notebook( self.notebook.object_id, read_write = True, owner = True ) )
    self.database.execute( self.user.sql_save_notebook( self.notebook.trash_id, read_write = True, owner = True ) )
    self.database.execute( self.user.sql_save_notebook( self.anon_notebook.object_id, read_write = False, owner = False ) )

  def make_users( self ):
    self.user = User.create( self.database.next_id( User ), self.username, self.password, self.email_address )
    self.database.save( self.user, commit = False )

    self.user2 = User.create( self.database.next_id( User ), self.username2, self.password2, self.email_address2 )
    self.user2.rate_plan = 1
    self.database.save( self.user2, commit = False )

    self.anonymous = User.create( self.database.next_id( User ), u"anonymous" )
    self.database.save( self.anonymous, commit = False )

  def tearDown( self ):
    if self.upload_thread:
      self.upload_thread.join()

  def test_download( self, filename = None, quote_filename = None, file_data = None, preview = None ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = filename or self.filename,
      file_data = file_data or self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    if quote_filename is None:
      quote_param = ""
    elif quote_filename is True:
      quote_param = "&quote_filename=True"
    else:
      quote_param = "&quote_filename=False"

    if preview is None:
      preview_param = ""
    elif preview is True:
      preview_param = "&preview=True"
    else:
      preview_param = "&preview=False"

    result = self.http_get(
      "/files/download?file_id=%s%s%s" % ( self.file_id, quote_param, preview_param ),
      session_id = self.session_id,
    )

    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == self.content_type

    filename = ( filename or self.filename ).encode( "utf8" )
    if quote_filename is True:
      filename = urllib.quote( filename )
    assert headers[ u"Content-Disposition" ] == 'attachment; filename="%s"' % filename

    gen = result[ u"body" ]
    assert isinstance( gen, types.GeneratorType )
    pieces = []

    try:
      for piece in gen:
        pieces.append( piece )
    except AttributeError, exc:
      if u"session_storage" not in str( exc ):
        raise exc

    file_data = "".join( pieces )
    assert file_data == ( file_data or self.file_data )

  def test_download_with_unicode_filename( self ):
    self.test_download( self.unicode_filename )

  def test_download_with_unicode_quoted_filename( self ):
    self.test_download( self.unicode_filename, quote_filename = True )

  def test_download_with_unicode_unquoted_filename( self ):
    self.test_download( self.unicode_filename, quote_filename = False )

  IMAGE_DATA = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x06bKGD\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xd7\x06\r\x13(:;\xf4\xc1{\x00\x00\x00\x1dtEXtComment\x00Created with The GIMP\xefd%n\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xf5\xeb\x17\x00\x05\xe0\x02\xefIj\xd4!\x00\x00\x00\x00IEND\xaeB`\x82'

  def test_download_image( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.IMAGE_DATA,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/download?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert result[ u"redirect" ] == u"/files/preview?file_id=%s&quote_filename=False" % self.file_id

  def test_download_image_with_preview_true( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.IMAGE_DATA,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/download?file_id=%s&preview=true" % self.file_id,
      session_id = self.session_id,
    )

    assert result[ u"redirect" ] == u"/files/preview?file_id=%s&quote_filename=False" % self.file_id

  def test_download_image_with_preview_true_and_quote_filename_true( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.IMAGE_DATA,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/download?file_id=%s&preview=true&quote_filename=True" % self.file_id,
      session_id = self.session_id,
    )

    assert result[ u"redirect" ] == u"/files/preview?file_id=%s&quote_filename=True" % self.file_id

  def test_download_image_with_preview_false( self ):
    self.test_download( file_data = self.IMAGE_DATA, preview = False )

  def test_download_non_image_with_preview_true( self ):
    self.test_download( preview = True )

  def test_download_non_image_with_preview_false( self ):
    self.test_download( preview = False )

  def test_download_without_login( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    path = "/files/download?file_id=%s" % self.file_id
    result = self.http_get( path )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def test_download_without_access( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.login2()

    result = self.http_get(
      "/files/download?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ u"body" ][ 0 ]

  def test_download_with_unknown_file_id( self ):
    self.login()

    result = self.http_get(
      "/files/download?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ u"body" ][ 0 ]

  def test_preview( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.IMAGE_DATA,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/preview?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert result[ u"file_id" ] == self.file_id
    assert result[ u"filename" ] == self.filename
    assert result[ u"quote_filename" ] == False

  def test_preview_with_quote_filename_true( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.IMAGE_DATA,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/preview?file_id=%s&quote_filename=true" % self.file_id,
      session_id = self.session_id,
    )

    assert result[ u"file_id" ] == self.file_id
    assert result[ u"filename" ] == self.filename
    assert result[ u"quote_filename" ] == True

  def test_preview_with_quote_filename_false( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.IMAGE_DATA,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/preview?file_id=%s&quote_filename=false" % self.file_id,
      session_id = self.session_id,
    )

    assert result[ u"file_id" ] == self.file_id
    assert result[ u"filename" ] == self.filename
    assert result[ u"quote_filename" ] == False

  def test_preview_without_login( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    path = "/files/preview?file_id=%s" % self.file_id
    result = self.http_get( path )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def test_preview_without_access( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.login2()

    result = self.http_get(
      "/files/preview?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ u"error" ]

  def test_preview_with_unknown_file_id( self ):
    self.login()

    result = self.http_get(
      "/files/preview?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ u"error" ]

  def test_thumbnail( self ):
    self.login()

    # make the test image big enough to require scaling down
    image = Image.open( StringIO( self.IMAGE_DATA ) )
    image = image.transform( ( 250, 250 ), Image.QUAD, range( 8 ) )

    image_data = StringIO()
    image.save( image_data, "PNG" )

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = image_data.getvalue(),
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/thumbnail?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == self.content_type
    assert u"Content-Disposition" not in headers

    file_data = "".join( result[ u"body" ] )
    image = Image.open( StringIO( file_data ) )
    assert image
    assert image.size == ( 125, 125 )

  def test_thumbnail_without_scaling( self ):
    self.login()

    # make the test image small enough so that no scaling is performed
    image = Image.open( StringIO( self.IMAGE_DATA ) )
    image = image.transform( ( 100, 100 ), Image.QUAD, range( 8 ) )

    image_data = StringIO()
    image.save( image_data, "PNG" )

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = image_data.getvalue(),
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/thumbnail?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == self.content_type
    assert u"Content-Disposition" not in headers

    file_data = "".join( result[ u"body" ] )
    image = Image.open( StringIO( file_data ) )
    assert image
    assert image.size == ( 100, 100 )

  def test_thumbnail_different_dimensions( self ):
    self.login()

    # make the test image small enough so that no scaling is performed
    image = Image.open( StringIO( self.IMAGE_DATA ) )
    image = image.transform( ( 250, 100 ), Image.QUAD, range( 8 ) )

    image_data = StringIO()
    image.save( image_data, "PNG" )

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = image_data.getvalue(),
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/thumbnail?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == self.content_type
    assert u"Content-Disposition" not in headers

    file_data = "".join( result[ u"body" ] )
    image = Image.open( StringIO( file_data ) )
    assert image
    assert image.size == ( 125, 50 )

  def test_thumbnail_with_max_size( self ):
    self.login()

    # make the test image big enough to require scaling down
    image = Image.open( StringIO( self.IMAGE_DATA ) )
    image = image.transform( ( 250, 250 ), Image.QUAD, range( 8 ) )

    image_data = StringIO()
    image.save( image_data, "PNG" )

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = image_data.getvalue(),
      content_type = self.content_type,
      session_id = self.session_id,
    )

    max_size = 225
    result = self.http_get(
      "/files/thumbnail?file_id=%s&max_size=%s" % ( self.file_id, max_size ),
      session_id = self.session_id,
    )

    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == self.content_type
    assert u"Content-Disposition" not in headers

    file_data = "".join( result[ u"body" ] )
    image = Image.open( StringIO( file_data ) )
    assert image
    assert image.size == ( max_size, max_size )

  def test_thumbnail_with_max_size_without_scaling( self ):
    self.login()

    # make the test image big enough to require scaling down
    image = Image.open( StringIO( self.IMAGE_DATA ) )
    image = image.transform( ( 250, 250 ), Image.QUAD, range( 8 ) )

    image_data = StringIO()
    image.save( image_data, "PNG" )

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = image_data.getvalue(),
      content_type = self.content_type,
      session_id = self.session_id,
    )

    max_size = 300
    result = self.http_get(
      "/files/thumbnail?file_id=%s&max_size=%s" % ( self.file_id, max_size ),
      session_id = self.session_id,
    )

    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == self.content_type
    assert u"Content-Disposition" not in headers

    file_data = "".join( result[ u"body" ] )
    image = Image.open( StringIO( file_data ) )
    assert image
    assert image.size == ( 250, 250 )

  def test_thumbnail_with_non_image( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data, # not a valid image
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/thumbnail?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == self.content_type
    assert u"Content-Disposition" not in headers

    # should get the default thumbnail image
    file_data = "".join( result[ u"body" ] )
    image = Image.open( StringIO( file_data ) )
    assert image
    assert image.size[ 0 ] <= 125
    assert image.size[ 1 ] <= 125

  def test_thumbnail_without_login( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data, # not a valid image
      content_type = self.content_type,
      session_id = self.session_id,
    )

    path = "/files/thumbnail?file_id=%s" % self.file_id
    result = self.http_get( path )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def test_thumbnail_with_invalid_max_size( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data, # not a valid image
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/thumbnail?file_id=%s&max_size=0" % self.file_id,
      session_id = self.session_id,
    )

    assert u"max size" in result[ u"body" ][ 0 ]

  def test_thumbnail_without_access( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data, # not a valid image
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.login2()

    result = self.http_get(
      "/files/thumbnail?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ u"body" ][ 0 ]

  def test_thumbnail_with_unknown_file_id( self ):
    self.login()

    result = self.http_get(
      "/files/thumbnail?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ u"body" ][ 0 ]

  def test_image( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.IMAGE_DATA,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/image?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == self.content_type
    assert u"Content-Disposition" not in headers

    assert "".join( result[ u"body" ] ) == self.IMAGE_DATA

  def test_image_with_non_image( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/image?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == self.content_type
    assert u"Content-Disposition" not in headers

    assert "".join( result[ u"body" ] ) == self.file_data

  def test_image_without_login( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.IMAGE_DATA,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    path = "/files/image?file_id=%s" % self.file_id
    result = self.http_get( path )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def test_image_without_access( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.IMAGE_DATA,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.login2()

    result = self.http_get(
      "/files/image?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ u"body" ][ 0 ]

  def test_image_with_unknown_file_id( self ):
    self.login()

    result = self.http_get(
      "/files/image?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ u"body" ][ 0 ]

  def test_upload_page( self ):
    self.login()

    result = self.http_get(
      "/files/upload_page?notebook_id=%s&note_id=%s" % ( self.notebook.object_id, self.note.object_id ),
      session_id = self.session_id,
    )

    assert result.get( u"notebook_id" ) == self.notebook.object_id
    assert result.get( u"note_id" ) == self.note.object_id
    assert result.get( u"file_id" )
    assert u"attach" in result.get( u"label_text" )
    assert u"upload" in result.get( u"instructions_text" )

  def test_upload_page_without_login( self ):
    path = "/files/upload_page?notebook_id=%s&note_id=%s" % ( self.notebook.object_id, self.note.object_id )
    result = self.http_get( path )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def test_import_page( self ):
    self.login()

    result = self.http_get(
      "/files/import_page?notebook_id=%s" % self.notebook.object_id,
      session_id = self.session_id,
    )

    assert result.get( u"notebook_id" ) == self.notebook.object_id
    assert result.get( u"note_id" ) == None
    assert result.get( u"file_id" )
    assert u"import" in result.get( u"label_text" )
    assert u"import" in result.get( u"instructions_text" )

  def test_upload_page_without_login( self ):
    path = "/files/import_page?notebook_id=%s" % self.notebook.object_id
    result = self.http_get( path )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def test_upload( self, filename = None ):
    self.login()

    result = self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = filename or self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    assert u"body" not in result
    assert u"script" not in result

    # assert that the file metadata was actually stored in the database
    db_file = self.database.load( File, self.file_id )
    assert db_file
    assert db_file.notebook_id == self.notebook.object_id
    assert db_file.note_id == self.note.object_id
    assert db_file.filename == filename or self.filename
    assert db_file.size_bytes == len( self.file_data )
    assert db_file.content_type == self.content_type

    # assert that the file data was actually stored
    assert Upload_file.open_file( self.file_id ).read() == self.file_data

    # assert that storage bytes increased
    orig_storage_bytes = self.user.storage_bytes
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > orig_storage_bytes

  def test_upload_with_unicode_filename( self ):
    self.test_upload( self.unicode_filename )

  def test_upload_without_login( self ):
    result = self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
    )

    assert u"access" in result.get( u"script" )

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_upload_without_access( self ):
    self.login2()

    result = self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id
    )

    assert u"access" in result.get( u"script" )

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_upload_without_file_id( self ):
    self.login()

    result = self.http_upload(
      "/files/upload",
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id
    )

    assert u"error" in result[ u"body" ][ 0 ]

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_upload_unnamed( self ):
    self.login()

    result = self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = "",
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id
    )

    assert "select a file" in result[ "script" ]

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_upload_invalid_content_length( self ):
    self.login()

    result = self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      headers = [ ( "Content-Length", "-10" ) ],
      session_id = self.session_id
    )

    assert u"error" in result[ u"body" ][ 0 ]

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_upload_cancel( self ):
    self.login()

    result = self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      simulate_cancel = True,
      session_id = self.session_id
    )

    assert u"body" not in result
    assert u"script" not in result

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_upload_over_quota( self ):
    large_file_data = self.file_data * 5

    self.login()

    result = self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = large_file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    assert "quota" in result[ "script" ]

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def assert_streaming_error( self, result, error_string ):
    gen = result[ u"body" ]
    assert isinstance( gen, types.GeneratorType )

    found_error = False

    try:
      for piece in gen:
        if error_string in piece:
          found_error = True
    except AttributeError, exc:
      if u"session_storage" not in str( exc ):
        raise exc

    assert found_error

  def test_progress( self ):
    self.database.execute( self.user2.sql_save_notebook( self.notebook.object_id, read_write = True, owner = False ) )
    self.database.execute( self.user2.sql_save_notebook( self.notebook.trash_id, read_write = True, owner = False ) )

    self.login2()
    self.database.save( File( object_id = self.file_id ) )

    # start a file uploading in a separate thread
    def upload():
      self.http_upload(
        "/files/upload?file_id=%s" % self.file_id,
        dict(
          notebook_id = self.notebook.object_id,
          note_id = self.note.object_id,
        ),
        filename = self.filename,
        file_data = self.file_data * 1000,
        content_type = self.content_type,
        session_id = self.session_id,
      )

    self.upload_thread = Thread( target = upload )
    self.upload_thread.start()

    # report on that file's upload progress
    result = self.http_get(
      "/files/progress?file_id=%s&filename=%s" % ( self.file_id, self.filename ),
      session_id = self.session_id,
    )

    gen = result[ u"body" ]
    assert isinstance( gen, types.GeneratorType )

    tick_count = 0
    tick_done = False
    complete = False

    try:
      for piece in gen:
        if u"tick(" in piece:
          tick_count += 1
        if u"tick(1.0)" in piece:
          tick_done = True
        if u"complete" in piece:
          complete = True
    # during this unit test, full session info isn't available, so swallow an expected
    # exception about session_storage
    except AttributeError, exc:
      if u"session_storage" not in str( exc ):
        raise exc

    # assert that the progress bar is moving, and then completes
    assert tick_count >= 2
    assert tick_done
    assert complete

  def test_progress_without_login( self ):
    self.database.execute( self.user2.sql_save_notebook( self.notebook.object_id, read_write = True, owner = False ) )
    self.database.execute( self.user2.sql_save_notebook( self.notebook.trash_id, read_write = True, owner = False ) )

    self.login2() # this login is for the upload, not the call to progress
    self.database.save( File( object_id = self.file_id ) )

    # start a file uploading in a separate thread
    def upload():
      self.http_upload(
        "/files/upload?file_id=%s" % self.file_id,
        dict(
          notebook_id = self.notebook.object_id,
          note_id = self.note.object_id,
        ),
        filename = self.filename,
        file_data = self.file_data * 1000,
        content_type = self.content_type,
        session_id = self.session_id,
      )

    self.upload_thread = Thread( target = upload )
    self.upload_thread.start()

    # report on that file's upload progress
    path = "/files/progress?file_id=%s&filename=%s" % ( self.file_id, self.filename )
    result = self.http_get( path )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def test_progress_for_completed_upload( self ):
    self.login()
    self.database.save( File( object_id = self.file_id ) )

    # upload a file completely
    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    # report on that completed file's upload progress
    result = self.http_get(
      "/files/progress?file_id=%s&filename=%s" % ( self.file_id, self.filename ),
      session_id = self.session_id,
    )

    gen = result[ u"body" ]
    assert isinstance( gen, types.GeneratorType )

    complete = False

    try:
      for piece in gen:
        if u"complete" in piece:
          complete = True
    # during this unit test, full session info isn't available, so swallow an expected
    # exception about session_storage
    except AttributeError, exc:
      if u"session_storage" not in str( exc ):
        raise exc

    # assert that the progress bar is moving, and then completes
    assert complete

  def test_progress_with_unknown_file_id( self ):
    self.login()

    result = self.http_get(
      "/files/progress?file_id=%s&filename=%s" % ( self.file_id, self.filename ),
      session_id = self.session_id,
    )

    assert u"error" in result[ u"body" ][ 0 ]
    assert u"unknown" in result[ u"body" ][ 0 ]

  def test_progress_over_quota( self ):
    self.login()
    self.database.save( File( object_id = self.file_id ) )

    # start a large file uploading in a separate thread
    def upload():
      self.http_upload(
        "/files/upload?file_id=%s" % self.file_id,
        dict(
          notebook_id = self.notebook.object_id,
          note_id = self.note.object_id,
        ),
        filename = self.filename,
        file_data = self.file_data * 1000,
        content_type = self.content_type,
        session_id = self.session_id,
      )

    self.upload_thread = Thread( target = upload )
    self.upload_thread.start()

    result = self.http_get(
      "/files/progress?file_id=%s&filename=%s" % ( self.file_id, self.filename ),
      session_id = self.session_id,
    )

    self.assert_streaming_error( result, u"quota" )

  def test_stats( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/stats?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert result[ u"filename" ] == self.filename
    assert result[ u"size_bytes" ] == len( self.file_data )

    orig_storage_bytes = self.user.storage_bytes
    user = self.database.load( User, self.user.object_id )
    assert result[ u"storage_bytes" ] == user.storage_bytes
    assert user.storage_bytes > orig_storage_bytes

  def test_stats_without_login( self ):
    self.login() # this login is for the upload, not the call to stats

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    path = "/files/stats?file_id=%s" % self.file_id
    result = self.http_get( path )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def test_stats_without_access( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.login2() # now login as a different user

    result = self.http_get(
      "/files/stats?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ u"error" ]

  def test_stats_with_unknown_file_id( self ):
    self.login()

    result = self.http_get(
      "/files/stats?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ u"error" ]

  def test_delete( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post(
      "/files/delete",
      dict(
        file_id = self.file_id,
      ),
      session_id = self.session_id,
    )

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

    orig_storage_bytes = self.user.storage_bytes
    user = self.database.load( User, self.user.object_id )
    assert result[ u"storage_bytes" ] == user.storage_bytes
    assert user.storage_bytes != orig_storage_bytes

  def test_delete_without_login( self ):
    self.login() # this login is for the upload, not the call to delete

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post(
      "/files/delete",
      dict(
        file_id = self.file_id,
      ),
    )

    assert u"access" in result[ u"error" ]

  def test_delete_without_access( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.login2() # now login as a different user

    result = self.http_post(
      "/files/delete",
      dict(
        file_id = self.file_id,
      ),
      session_id = self.session_id,
    )

    assert u"access" in result[ u"error" ]

  def test_delete_with_unknown_file_id( self ):
    self.login()

    result = self.http_post(
      "/files/delete",
      dict(
        file_id = self.file_id,
      ),
      session_id = self.session_id,
    )

    assert u"access" in result[ u"error" ]

  def test_rename( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post(
      "/files/rename",
      dict(
        file_id = self.file_id,
        filename = self.new_filename,
      ),
      session_id = self.session_id,
    )

    assert u"error" not in result
    assert u"body" not in result

    db_file = self.database.load( File, self.file_id )
    assert db_file
    assert db_file.filename == self.new_filename
    assert Upload_file.exists( self.file_id )

  def test_rename_with_weird_filename( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post(
      "/files/rename",
      dict(
        file_id = self.file_id,
        filename = self.weird_filename,
      ),
      session_id = self.session_id,
    )

    assert u"error" not in result
    assert u"body" not in result

    db_file = self.database.load( File, self.file_id )
    assert db_file
    assert db_file.filename == self.weird_filename
    assert Upload_file.exists( self.file_id )

  def test_rename_without_login( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post(
      "/files/rename",
      dict(
        file_id = self.file_id,
        filename = self.new_filename,
      ),
    )

    assert u"access" in result[ u"error" ]

    db_file = self.database.load( File, self.file_id )
    assert db_file
    assert db_file.filename == self.filename
    assert Upload_file.exists( self.file_id )

  def test_rename_without_access( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.login2()

    result = self.http_post(
      "/files/rename",
      dict(
        file_id = self.file_id,
        filename = self.new_filename,
      ),
      session_id = self.session_id,
    )

    assert u"access" in result[ u"error" ]

    db_file = self.database.load( File, self.file_id )
    assert db_file
    assert db_file.filename == self.filename
    assert Upload_file.exists( self.file_id )

  def test_rename_with_unknown_file_id( self ):
    self.login()

    result = self.http_post(
      "/files/rename",
      dict(
        file_id = self.file_id,
        filename = self.new_filename,
      ),
      session_id = self.session_id,
    )

    assert u"access" in result[ u"error" ]

  def test_parse_csv( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5'
    expected_rows = [
      [ "label 1", "label 2", "label 3" ],
      [ "5", "blah and stuff", "3.3" ],
      [ "8", "whee", "hmm\nfoo" ],
      [ "3", "4", "5" ],
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

    parser = cherrypy.root.files.parse_csv( self.file_id )

    for ( index, row ) in enumerate( parser ):
      assert row == expected_rows[ index ]

    assert index == len( expected_rows ) - 1

  @raises( Parse_error )
  def test_parse_csv_empty( self ):
    self.login()

    csv_data = ""

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

    parser = cherrypy.root.files.parse_csv( self.file_id )
    parser.next()

  @raises( Parse_error )
  def test_parse_csv_invalid_text( self ):
    self.login()

    csv_data = '"See, Vera? Dress yourself up, you get taken out somewhere fun. -- Jayne'

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

    parser = cherrypy.root.files.parse_csv( self.file_id )
    parser.next()

  @raises( Parse_error )
  def test_parse_csv_invalid_binary( self ):
    self.login()

    csv_data = self.file_data + "\x00"

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

    parser = cherrypy.root.files.parse_csv( self.file_id )
    parser.next()

  def test_parse_csv_embedded_quotes( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah ""and"" stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5'
    expected_rows = [
      [ "label 1", "label 2", "label 3" ],
      [ "5", 'blah "and" stuff', "3.3" ],
      [ "8", "whee", "hmm\nfoo" ],
      [ "3", "4", "5" ],
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

    parser = cherrypy.root.files.parse_csv( self.file_id )

    for ( index, row ) in enumerate( parser ):
      assert row == expected_rows[ index ]

    assert index == len( expected_rows ) - 1

  @raises( Parse_error )
  def test_parse_csv_different_row_element_counts( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff"\n"8","whee","hmm\nfoo",4.4\n3,4,5'

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

    parser = cherrypy.root.files.parse_csv( self.file_id )

    for row in parser:
      pass

  def test_parse_csv_empty_rows( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n\n3,4,5'
    expected_rows = [
      [ "label 1", "label 2", "label 3" ],
      [ "5", "blah and stuff", "3.3" ],
      [ "8", "whee", "hmm\nfoo" ],
      [ "3", "4", "5" ],
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

    parser = cherrypy.root.files.parse_csv( self.file_id )

    for ( index, row ) in enumerate( parser ):
      assert row == expected_rows[ index ]

    assert index == len( expected_rows ) - 1

  @raises( Parse_error )
  def test_parse_csv_unknown_file_id( self ):
    parser = cherrypy.root.files.parse_csv( u"unknownfileid" )

    for row in parser:
      pass

  def test_parse_csv_without_header( self ):
    self.login()

    csv_data = '5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5'
    expected_rows = [
      [ "5", "blah and stuff", "3.3" ],
      [ "8", "whee", "hmm\nfoo" ],
      [ "3", "4", "5" ],
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

    parser = cherrypy.root.files.parse_csv( self.file_id )

    for ( index, row ) in enumerate( parser ):
      assert row == expected_rows[ index ]

    assert index == len( expected_rows ) - 1

  def test_parse_csv_skip_header( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5'
    expected_rows = [
      [ "5", "blah and stuff", "3.3" ],
      [ "8", "whee", "hmm\nfoo" ],
      [ "3", "4", "5" ],
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

    parser = cherrypy.root.files.parse_csv( self.file_id, skip_header = True )

    for ( index, row ) in enumerate( parser ):
      assert row == expected_rows[ index ]

    assert index == len( expected_rows ) - 1

  def test_parse_csv_skip_header_without_header( self ):
    self.login()

    csv_data = '5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5'
    expected_rows = [
      [ "5", "blah and stuff", "3.3" ],
      [ "8", "whee", "hmm\nfoo" ],
      [ "3", "4", "5" ],
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

    parser = cherrypy.root.files.parse_csv( self.file_id, skip_header = True )

    for ( index, row ) in enumerate( parser ):
      assert row == expected_rows[ index ]

    assert index == len( expected_rows ) - 1

  def test_csv_head( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5\n6,7,8\n"yay",9,10'
    expected_rows = [
      [ "label 1", "label 2", "label 3" ],
      [ "5", "blah and stuff", "3.3" ],
      [ "8", "whee", "hmm\nfoo" ],
      [ "3", "4", "5" ],
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

    result = self.http_get(
      "/files/csv_head?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert result[ u"file_id" ] == self.file_id

    for ( index, row ) in enumerate( result[ u"rows" ] ):
      assert row == expected_rows[ index ]

    assert index == len( expected_rows ) - 1

  def test_csv_head_without_login( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5\n6,7,8\n"yay",9,10'

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

    path = "/files/csv_head?file_id=%s" % self.file_id
    result = self.http_get( path )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def test_csv_head_without_access( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5\n6,7,8\n"yay",9,10'

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

    self.login2()

    result = self.http_get(
      "/files/csv_head?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ "error" ]

  def test_csv_head_unknown_file_id( self ):
    self.login()

    result = self.http_get(
      "/files/csv_head?file_id=unknownfileid",
      session_id = self.session_id,
    )

    assert u"access" in result[ "error" ]

  def test_csv_head_few_rows( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3'
    expected_rows = [
      [ "label 1", "label 2", "label 3" ],
      [ "5", "blah and stuff", "3.3" ],
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

    result = self.http_get(
      "/files/csv_head?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert result[ u"file_id" ] == self.file_id

    for ( index, row ) in enumerate( result[ u"rows" ] ):
      assert row == expected_rows[ index ]

    assert index == len( expected_rows ) - 1

  def test_csv_head_large_elements( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"Yes. Yes, this is a fertile land, and we will thrive. We will rule over all this land, and we will call it... This Land.",3.3\n"8","whee","hmm\nfoo"\n3,4,5\n6,7,8\n"yay",9,10'
    expected_rows = [
      [ "label 1", "label 2", "label 3" ],
      [ "5", "Yes. Yes, this is a fertile la ...", "3.3" ],
      [ "8", "whee", "hmm\nfoo" ],
      [ "3", "4", "5" ],
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

    result = self.http_get(
      "/files/csv_head?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert result[ u"file_id" ] == self.file_id

    for ( index, row ) in enumerate( result[ u"rows" ] ):
      assert row == expected_rows[ index ]

    assert index == len( expected_rows ) - 1

  def test_csv_head_many_elements_per_row( self ):
    self.login()

    row0 = '1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22'
    row1 = 'a,b,c,d,e,f,g,h,i,i,j,k,l,m,n,o,p,q,r,s,t,u'
    csv_data = '%s\n%s\n' % ( row0, row1 )

    expected_rows = [
      row0.split( ',' )[ : 20 ],
      row1.split( ',' )[ : 20 ],
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

    result = self.http_get(
      "/files/csv_head?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert result[ u"file_id" ] == self.file_id

    for ( index, row ) in enumerate( result[ u"rows" ] ):
      assert row == expected_rows[ index ]

    assert index == len( expected_rows ) - 1

  def test_purge_unused( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    # the file is not linked to from the note's contents, so this should delete it
    cherrypy.root.files.purge_unused( self.note )

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_purge_unused_empty_link( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.note.contents = '<a href="/files/download?file_id=%s"></a>' % self.file_id
    self.database.save( self.note )

    # the file is linked to from the note's contents but the link title is empty, so this should
    # delete it
    cherrypy.root.files.purge_unused( self.note )

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_purge_unused_empty_link_with_quote_filename( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.note.contents = '<a href="/files/download?file_id=%s&quote_filename=true"></a>' % self.file_id
    self.database.save( self.note )

    # the file is linked to from the note's contents but the link title is empty, so this should
    # delete it
    cherrypy.root.files.purge_unused( self.note )

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_purge_unused_keep_file( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.note.contents = '<a href="/files/download?file_id=%s">file link</a>' % self.file_id
    self.database.save( self.note )

    # the file is linked to from the note's contents, so this should not delete it
    cherrypy.root.files.purge_unused( self.note )

    db_file = self.database.load( File, self.file_id )
    assert db_file
    assert db_file.object_id == self.file_id
    assert db_file.filename == self.filename
    assert Upload_file.exists( self.file_id )

  def test_purge_unused_keep_image_file( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.note.contents = '<a href="/files/download?file_id=%s"><img src="/blah"></a>' % self.file_id
    self.database.save( self.note )

    # the image file is linked to from the note's contents, so this should not delete it
    cherrypy.root.files.purge_unused( self.note )

    db_file = self.database.load( File, self.file_id )
    assert db_file
    assert db_file.object_id == self.file_id
    assert db_file.filename == self.filename
    assert Upload_file.exists( self.file_id )

  def test_purge_unused_keep_file_with_quote_filename( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.note.contents = '<a href="/files/download?file_id=%s&quote_filename=false">file link</a>' % self.file_id
    self.database.save( self.note )

    # the file is linked to from the note's contents, so this should not delete it
    cherrypy.root.files.purge_unused( self.note )

    db_file = self.database.load( File, self.file_id )
    assert db_file
    assert db_file.object_id == self.file_id
    assert db_file.filename == self.filename
    assert Upload_file.exists( self.file_id )

  def test_purge_unused_all_links( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.note.contents = '<a href="/files/download?file_id=%s">file link</a>' % self.file_id
    self.database.save( self.note )

    # the file is linked to from the note's contents, but because of the purge_all_links flag, it
    # should be deleted anyway
    cherrypy.root.files.purge_unused( self.note, purge_all_links = True )

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_purge_unused_all_links_with_quote_filename( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.note.contents = '<a href="/files/download?file_id=%s&quote_filename=true">file link</a>' % self.file_id
    self.database.save( self.note )

    # the file is linked to from the note's contents, but because of the purge_all_links flag, it
    # should be deleted anyway
    cherrypy.root.files.purge_unused( self.note, purge_all_links = True )

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_purge_unused_multiple_files( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.note.contents = '<a href="/files/download?file_id=%s">file link</a>' % self.file_id
    self.database.save( self.note )

    other_file_id = u"23"
    self.http_upload(
      "/files/upload?file_id=%s" % other_file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = u"otherfile.png",
      file_data = u"whee",
      content_type = self.content_type,
      session_id = self.session_id,
    )

    # one file is linked from the note's contents but the other is not. the file that is not linked
    # should be deleted
    cherrypy.root.files.purge_unused( self.note )

    db_file = self.database.load( File, self.file_id )
    assert db_file
    assert db_file.object_id == self.file_id
    assert db_file.filename == self.filename
    assert Upload_file.exists( self.file_id )

    other_db_file = self.database.load( File, other_file_id )
    assert other_db_file is None
    assert not Upload_file.exists( other_file_id )

  def test_purge_unused_multiple_files( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.note.contents = '<a href="/files/download?file_id=%s">file link</a>' % self.file_id
    self.database.save( self.note )

    other_file_id = u"23"
    self.http_upload(
      "/files/upload?file_id=%s" % other_file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = u"otherfile.png",
      file_data = u"whee",
      content_type = self.content_type,
      session_id = self.session_id,
    )

    # one file is linked from the note's contents but the other is not. the file that is not linked
    # should be deleted
    cherrypy.root.files.purge_unused( self.note )

    db_file = self.database.load( File, self.file_id )
    assert db_file
    assert db_file.object_id == self.file_id
    assert db_file.filename == self.filename
    assert Upload_file.exists( self.file_id )

    other_db_file = self.database.load( File, other_file_id )
    assert other_db_file is None
    assert not Upload_file.exists( other_file_id )

  def test_purge_unused_multiple_files_with_quote_filename( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.note.contents = '<a href="/files/download?file_id=%s&quote_filename=false">file link</a>' % self.file_id
    self.database.save( self.note )

    other_file_id = u"23"
    self.http_upload(
      "/files/upload?file_id=%s" % other_file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = u"otherfile.png",
      file_data = u"whee",
      content_type = self.content_type,
      session_id = self.session_id,
    )

    # one file is linked from the note's contents but the other is not. the file that is not linked
    # should be deleted
    cherrypy.root.files.purge_unused( self.note )

    db_file = self.database.load( File, self.file_id )
    assert db_file
    assert db_file.object_id == self.file_id
    assert db_file.filename == self.filename
    assert Upload_file.exists( self.file_id )

    other_db_file = self.database.load( File, other_file_id )
    assert other_db_file is None
    assert not Upload_file.exists( other_file_id )

  def test_purge_unused_multiple_image_files( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.note.contents = '<a href="/files/download?file_id=%s"><img src="/blah"></a>' % self.file_id
    self.database.save( self.note )

    other_file_id = u"23"
    self.http_upload(
      "/files/upload?file_id=%s" % other_file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = u"otherfile.png",
      file_data = u"whee",
      content_type = self.content_type,
      session_id = self.session_id,
    )

    # one images file is linked from the note's contents but the other is not. the file that is not
    # linked should be deleted
    cherrypy.root.files.purge_unused( self.note )

    db_file = self.database.load( File, self.file_id )
    assert db_file
    assert db_file.object_id == self.file_id
    assert db_file.filename == self.filename
    assert Upload_file.exists( self.file_id )

    other_db_file = self.database.load( File, other_file_id )
    assert other_db_file is None
    assert not Upload_file.exists( other_file_id )

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
