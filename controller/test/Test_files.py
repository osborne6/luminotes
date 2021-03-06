# -*- coding: utf8 -*-

import os
import time
import types
import urllib
import httplib
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
from model.Download_access import Download_access
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
      pass

    Upload_file.open_file = open_file
    Upload_file.open_image = open_image
    Upload_file.delete_file = delete_file
    Upload_file.exists = exists
    Upload_file.close = close

    # write a test product file
    test_product_file = file( u"products/test.exe", "wb" )
    test_product_file.write( self.file_data )
    test_product_file.close()

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

    os.remove( u"products/test.exe" )

  def test_download( self, filename = None, quote_filename = None, file_data = None, preview = None, expected_file_data = None ):
    self.login()

    if expected_file_data is None:
      expected_file_data = file_data
      if file_data is None:
        expected_file_data = self.file_data

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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

    received_file_data = "".join( pieces )
    assert received_file_data == expected_file_data

    return result

  def test_download_with_nginx( self ):
    cherrypy.root.files._Files__web_server = u"nginx"
    result = self.test_download( self.filename, expected_file_data = "" )

    headers = result[ u"headers" ]
    assert headers[ u"X-Accel-Redirect" ] == u"/download/%s" % self.file_id

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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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

  def test_download_product( self ):
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"txn"

    self.login()

    download_access = Download_access.create( access_id, item_number, transaction_id )
    self.database.save( download_access )

    result = self.http_get(
      "/files/download_product?access_id=%s" % access_id,
      session_id = self.session_id,
    )

    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == u"application/octet-stream"

    filename = u"test.exe".encode( "utf8" )
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
    assert file_data == self.file_data

  def test_download_product_with_nginx( self ):
    cherrypy.root.files._Files__web_server = u"nginx"
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"txn"

    self.login()

    download_access = Download_access.create( access_id, item_number, transaction_id )
    self.database.save( download_access )

    result = self.http_get(
      "/files/download_product?access_id=%s" % access_id,
      session_id = self.session_id,
    )

    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == u"application/octet-stream"

    filename = u"test.exe".encode( "utf8" )
    assert headers[ u"Content-Disposition" ] == 'attachment; filename="%s"' % filename
    assert headers[ u"X-Accel-Redirect" ] == u"/download_product/test.exe"

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
    assert file_data == u""

  def test_download_product_without_login( self ):
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"txn"

    download_access = Download_access.create( access_id, item_number, transaction_id )
    self.database.save( download_access )

    result = self.http_get(
      "/files/download_product?access_id=%s" % access_id,
    )

    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == u"application/octet-stream"

    filename = u"test.exe".encode( "utf8" )
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
    assert file_data == self.file_data

  def test_download_product_unknown_access_id( self ):
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"txn"

    self.login()

    download_access = Download_access.create( access_id, item_number, transaction_id )
    self.database.save( download_access )

    result = self.http_get(
      "/files/download_product?access_id=%s" % u"unknown_id",
      session_id = self.session_id,
    )

    assert u"access" in result[ u"body" ][ 0 ]
    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == u"text/html"
    assert not headers.get( u"Content-Disposition" )

  def test_download_product_missing_file( self ):
    access_id = u"wheeaccessid"
    item_number = u"5000"
    transaction_id = u"txn"
    self.settings[ u"global" ][ u"luminotes.download_products" ][ 0 ][ u"filename" ] = u"notthere.exe"

    self.login()

    download_access = Download_access.create( access_id, item_number, transaction_id )
    self.database.save( download_access )

    result = self.http_get(
      "/files/download_product?access_id=%s" % access_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ u"body" ][ 0 ]
    headers = result[ u"headers" ]
    assert headers
    assert headers[ u"Content-Type" ] == u"text/html"
    assert not headers.get( u"Content-Disposition" )

  def test_preview( self ):
    self.login()

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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

  def test_preview_with_unicode_filename( self ):
    self.login()

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.unicode_filename,
      file_data = self.IMAGE_DATA,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/preview?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert result[ u"file_id" ] == self.file_id
    assert result[ u"filename" ] == self.unicode_filename
    assert result[ u"quote_filename" ] == False

  def test_preview_with_quote_filename_true( self ):
    self.login()

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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

  def test_image_with_nginx( self ):
    cherrypy.root.files._Files__web_server = u"nginx"
    self.login()

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
    assert headers[ u"X-Accel-Redirect" ] == u"/download/%s" % self.file_id

    assert "".join( result[ u"body" ] ) == u""

  def test_image_with_non_image( self ):
    self.login()

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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

  def test_upload_id( self ):
    self.login()

    result = self.http_get(
      "/files/upload_id?notebook_id=%s&note_id=%s" % ( self.notebook.object_id, self.note.object_id ),
      session_id = self.session_id,
    )

    assert result.get( u"file_id" )

  def test_upload_id_without_login( self ):
    path = "/files/upload_id?notebook_id=%s&note_id=%s" % ( self.notebook.object_id, self.note.object_id )
    result = self.http_get( path )

    headers = result.get( "headers" )
    assert headers
    assert headers.get( "Location" ) == u"http:///login?after_login=%s" % urllib.quote( path )

  def test_upload_id_own_notes( self ):
    self.login()

    self.database.execute( self.user.sql_update_access( 
      self.notebook.object_id, read_write = Notebook.READ_WRITE_FOR_OWN_NOTES, owner = False,
    ) )

    result = self.http_get(
      "/files/upload_id?notebook_id=%s&note_id=%s" % ( self.notebook.object_id, self.note.object_id ),
      session_id = self.session_id,
    )

    assert u"access" in result[ u"error" ]

  def test_upload( self, filename = None ):
    self.login()
    orig_storage_bytes = self.user.storage_bytes

    result = self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > orig_storage_bytes

  def test_upload_with_unicode_filename( self ):
    self.test_upload( self.unicode_filename )

  def test_upload_own_notes( self ):
    self.login()

    self.database.execute( self.user.sql_update_access( 
      self.notebook.object_id, read_write = Notebook.READ_WRITE_FOR_OWN_NOTES, owner = False,
    ) )

    result = self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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

  def test_upload_without_login( self ):
    result = self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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

    assert "cancel_due_to_error" in result.get( u"script" )

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_upload_over_quota( self ):
    large_file_data = self.file_data * 5

    self.login()

    result = self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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

  def test_upload_no_quota( self ):
    large_file_data = self.file_data * 5
    self.settings[ u"global" ][ u"luminotes.rate_plans" ][ 0 ][ u"storage_quota_bytes" ] = None

    self.login()
    orig_storage_bytes = self.user.storage_bytes

    result = self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = large_file_data,
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
    assert db_file.filename == self.filename
    assert db_file.size_bytes == len( large_file_data )
    assert db_file.content_type == self.content_type

    # assert that the file data was actually stored
    assert Upload_file.open_file( self.file_id ).read() == large_file_data

    # assert that storage bytes increased
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > orig_storage_bytes

  def test_progress( self ):
    self.database.execute( self.user2.sql_save_notebook( self.notebook.object_id, read_write = True, owner = False ) )
    self.database.execute( self.user2.sql_save_notebook( self.notebook.trash_id, read_write = True, owner = False ) )

    self.login2()
    self.database.save( File( object_id = self.file_id ) )

    # start a file uploading in a separate thread
    def upload():
      self.http_upload(
        "/files/upload?X-Progress-ID=%s" % self.file_id,
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

    result = self.http_get(
      "/files/progress?X-Progress-ID=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert result.get( u"state" ) == u"starting"

    self.upload_thread.start()

    received = 0
    size = 0
    previous_received = 0

    # report on that file's upload progress
    while True:
      result = self.http_get(
        "/files/progress?X-Progress-ID=%s" % self.file_id,
        session_id = self.session_id,
      )

      state = result.get( u"state" )
      assert state != "error"
      if state == "starting": continue
      if state == "done": break

      if state == "uploading":
        received = result.get( u"received" )
        size = result.get( u"size" )
        assert received
        assert size
        assert received < size
        assert received >= previous_received
        previous_received = received

  def test_progress_without_login( self ):
    self.database.execute( self.user2.sql_save_notebook( self.notebook.object_id, read_write = True, owner = False ) )
    self.database.execute( self.user2.sql_save_notebook( self.notebook.trash_id, read_write = True, owner = False ) )

    self.login2() # this login is for the upload, not the call to progress
    self.database.save( File( object_id = self.file_id ) )

    # start a file uploading in a separate thread
    def upload():
      self.http_upload(
        "/files/upload?X-Progress-ID=%s" % self.file_id,
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
    while True:
      path = "/files/progress?X-Progress-ID=%s" % self.file_id
      result = self.http_get( path )

      if result.get( u"state" ) != u"starting":
        break

    assert result.get( u"state" ) == u"error"
    assert result.get( u"status" ) == httplib.FORBIDDEN

  def test_progress_for_completed_upload( self ):
    self.login()
    self.database.save( File( object_id = self.file_id ) )

    # upload a file completely
    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/progress?X-Progress-ID=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert result.get( u"state" ) == u"done"

  def test_progress_with_unknown_file_id( self ):
    self.login()

    result = self.http_get(
      "/files/progress?X-Progress-ID=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert result.get( u"state" ) == u"error"
    assert result.get( u"status" ) == httplib.NOT_FOUND

  def test_progress_no_quota( self ):
    self.settings[ u"global" ][ u"luminotes.rate_plans" ][ 1 ][ u"storage_quota_bytes" ] = None
    self.test_progress()

  def test_stats( self ):
    self.login()
    orig_storage_bytes = self.user.storage_bytes

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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

    user = self.database.load( User, self.user.object_id )
    assert result[ u"storage_bytes" ] == user.storage_bytes
    assert user.storage_bytes > orig_storage_bytes

  def test_stats_own_notes( self ):
    self.login()

    self.database.execute( self.user.sql_update_access( 
      self.notebook.object_id, read_write = Notebook.READ_WRITE_FOR_OWN_NOTES, owner = False,
    ) )

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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

    assert u"access" in result[ "error" ]

  def test_stats_without_login( self ):
    self.login() # this login is for the upload, not the call to stats

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    orig_storage_bytes = self.user.storage_bytes

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

    user = self.database.load( User, self.user.object_id )
    assert result[ u"storage_bytes" ] == user.storage_bytes
    assert user.storage_bytes != orig_storage_bytes

  def test_delete_own_notes( self ):
    self.login()

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.database.execute( self.user.sql_update_access( 
      self.notebook.object_id, read_write = Notebook.READ_WRITE_FOR_OWN_NOTES, owner = False,
    ) )

    result = self.http_post(
      "/files/delete",
      dict(
        file_id = self.file_id,
      ),
      session_id = self.session_id,
    )

    assert u"access" in result[ "error" ]

  def test_delete_without_login( self ):
    self.login() # this login is for the upload, not the call to delete

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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

  def test_rename_own_notes( self ):
    self.login()

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.database.execute( self.user.sql_update_access( 
      self.notebook.object_id, read_write = Notebook.READ_WRITE_FOR_OWN_NOTES, owner = False,
    ) )

    result = self.http_post(
      "/files/rename",
      dict(
        file_id = self.file_id,
        filename = self.new_filename,
      ),
      session_id = self.session_id,
    )

    assert u"access" in result[ "error" ]

  def test_rename_with_weird_filename( self ):
    self.login()

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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

  def test_csv_head_own_notes( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5\n6,7,8\n"yay",9,10'
    expected_rows = [
      [ "label 1", "label 2", "label 3" ],
      [ "5", "blah and stuff", "3.3" ],
      [ "8", "whee", "hmm\nfoo" ],
      [ "3", "4", "5" ],
    ]

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = csv_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.database.execute( self.user.sql_update_access( 
      self.notebook.object_id, read_write = Notebook.READ_WRITE_FOR_OWN_NOTES, owner = False,
    ) )

    result = self.http_get(
      "/files/csv_head?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ "error" ]

  def test_csv_head_without_login( self ):
    self.login()

    csv_data = '"label 1","label 2","label 3"\n5,"blah and stuff",3.3\n"8","whee","hmm\nfoo"\n3,4,5\n6,7,8\n"yay",9,10'

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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

    result = self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    db_file = self.database.load( File, self.file_id )
    assert db_file

    # the file is not linked to from the note's contents, so this should delete it
    cherrypy.root.files.purge_unused( self.note )

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_purge_unused_empty_link( self ):
    self.login()

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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

  def test_purge_unused_keep_file_with_nofollow( self ):
    self.login()

    self.http_upload(
      "/files/upload?X-Progress-ID=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.note.contents = '<a href="/files/download?file_id=%s" rel="nofollow">file link</a>' % self.file_id
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % other_file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % other_file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % other_file_id,
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
      "/files/upload?X-Progress-ID=%s" % self.file_id,
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
      "/files/upload?X-Progress-ID=%s" % other_file_id,
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
