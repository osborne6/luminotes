import os
import re
import sys
import cgi
import time
import urllib
import os.path
import httplib
import tempfile
import cherrypy
from PIL import Image
from cStringIO import StringIO
from threading import Lock
from chardet.universaldetector import UniversalDetector
from Expose import expose
from Validate import validate, Valid_int, Valid_bool, Validation_error
from Database import Valid_id, end_transaction
from Users import grab_user_id, Access_error
from Expire import strongly_expire, weakly_expire
from model.File import File
from model.User import User
from model.Notebook import Notebook
from model.Download_access import Download_access
from view.Blank_page import Blank_page
from view.Json import Json
from view.Progress_bar import quota_error_script, general_error_script
from view.File_preview_page import File_preview_page


class Upload_error( Exception ):
  def __init__( self, message = None ):
    if message is None:
      message = u"An error occurred when uploading the file."

    Exception.__init__( self, message )
    self.__message = message

  def to_dict( self ):
    return dict(
      error = self.__message
    )


class Parse_error( Exception ):
  def __init__( self, message = None ):
    if message is None:
      message = u"Sorry, I can't figure out how to read that file. Please try a different file, or contact support for help."

    Exception.__init__( self, message )
    self.__message = message

  def to_dict( self ):
    return dict(
      error = self.__message
    )


# map of upload id to Upload_file
current_uploads = {}
current_uploads_lock = Lock()


def make_files_dir():
  if sys.platform.startswith( "win" ):
    files_dir = os.path.join( os.environ.get( "APPDATA" ), "Luminotes", "files" )
  else:
    files_dir = os.path.join( os.environ.get( "HOME", "" ), ".luminotes", "files" )

  if not os.path.exists( files_dir ):
    import stat
    os.makedirs( files_dir, stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR )

  return files_dir


files_dir = make_files_dir()


class Upload_file( object ):
  """
  File-like object for storing file uploads.
  """
  def __init__( self, file_id, filename, content_length ):
    self.__file = self.open_file( file_id, "w+" )
    self.__file_id = file_id
    self.__filename = filename
    self.__content_length = content_length
    self.__file_received_bytes = 0
    self.__total_received_bytes = cherrypy.request.rfile.bytes_read
  
  def write( self, data ):
    self.__file.write( data )
    self.__file_received_bytes += len( data )
    self.__total_received_bytes = cherrypy.request.rfile.bytes_read

  def tell( self ):
    return self.__file.tell()

  def seek( self, position ):
    self.__file.seek( position )

  def read( self, size = None ):
    if size is None:
      return self.__file.read()

    return self.__file.read( size )

  def close( self ):
    self.__file.close()

  def delete( self ):
    self.__file.close()
    self.delete_file( self.__file_id )

  @staticmethod
  def make_server_filename( file_id ):
    global files_dir
    return os.path.join( files_dir, u"%s" % file_id )

  @staticmethod
  def open_file( file_id, mode = None ):
    # force binary mode
    if not mode:
      mode = "rb"
    elif "b" not in mode:
      mode = "%sb" % mode

    return file( Upload_file.make_server_filename( file_id ), mode )

  @staticmethod
  def open_image( file_id ):
    return Image.open( Upload_file.make_server_filename( file_id ) )

  @staticmethod
  def delete_file( file_id ):
    return os.remove( Upload_file.make_server_filename( file_id ) )

  filename = property( lambda self: self.__filename )

  # expected byte count of the entire form upload, including the file and other form parameters
  content_length = property( lambda self: self.__content_length )

  # count of bytes received thus far for this file upload only
  file_received_bytes = property( lambda self: self.__file_received_bytes )

  # count of bytes received thus far for the form upload, including the file and other form
  # parameters
  total_received_bytes = property( lambda self: self.__total_received_bytes )


class FieldStorage( cherrypy._cpcgifs.FieldStorage ):
  """
  Derived from cherrypy._cpcgifs.FieldStorage, which is in turn derived from cgi.FieldStorage, which
  calls make_file() to create a temporary file where file uploads are stored. By wrapping this file
  object, we can track its progress as it's written. Inspired by:
  http://www.cherrypy.org/attachment/ticket/546/uploadfilter.py

  This method relies on a file_id parameter being present in the HTTP query string.

  @type binary: NoneType
  @param binary: ignored
  @rtype: Upload_file
  @return: wrapped temporary file used to store the upload
  @raise Upload_error: the provided file_id value is invalid, or the filename or Content-Length is
                       missing
  """
  def make_file( self, binary = None ):
    global current_uploads, current_uploads_lock

    cherrypy.response.timeout = 3600 * 2 # increase upload timeout to 2 hours (default is 5 min)
    cherrypy.server.socket_timeout = 60 # increase socket timeout to one minute (default is 10 sec)
    DASHES_AND_NEWLINES = 6 # four dashes and two newlines

    # pluck the file id out of the query string. it would be preferable to grab it out of parsed
    # form variables instead, but at this point in the processing, all the form variables might not
    # be parsed
    file_id = cgi.parse_qs( cherrypy.request.query_string ).get( u"file_id", [ None ] )[ 0 ]
    try:
      file_id = Valid_id()( file_id )
    except ValueError:
      raise Upload_error( "The file_id is invalid." )

    self.filename = unicode( self.filename.split( "/" )[ -1 ].split( "\\" )[ -1 ].strip(), "utf8" )

    if not self.filename:
      raise Upload_error( "Please provide a filename." )

    content_length =  cherrypy.request.headers.get( "content-length", 0 )
    try:
      content_length = Valid_int( min = 0 )( content_length ) - len( self.outerboundary ) - DASHES_AND_NEWLINES
    except ValueError:
      raise Upload_error( "The Content-Length header value is invalid." )

    # file size is the entire content length of the POST, minus the size of the other form
    # parameters and boundaries. note: this assumes that the uploaded file is sent as the last
    # form parameter in the POST
    existing_file = current_uploads.get( file_id )
    if existing_file:
      existing_file.close()

    upload_file = Upload_file( file_id, self.filename, content_length )

    current_uploads_lock.acquire()
    try:
      current_uploads[ file_id ] = upload_file
    finally:
      current_uploads_lock.release()

    return upload_file

  def __write( self, line ):
    """
    This implementation of __write() is different than that of the base class, because it calls
    make_file() whenever there is a filename instead of only for large enough files.
    """
    if self.__file is not None and self.filename:
        self.file = self.make_file( '' )
        self.file.write( self.__file.getvalue() )
        self.__file = None

    self.file.write( line )

cherrypy._cpcgifs.FieldStorage = FieldStorage


class Files( object ):
  FILE_LINK_PATTERN = re.compile( u'<a\s+href="[^"]*/files/download\?file_id=([^"&]+)(&[^"]*)?"[^>]*>(<img )?[^<]+</a>', re.IGNORECASE )

  """
  Controller for dealing with uploaded files, corresponding to the "/files" URL.
  """
  def __init__( self, database, users, download_products, web_server ):
    """
    Create a new Files object.

    @type database: controller.Database
    @param database: database that file metadata is stored in
    @type users: controller.Users
    @param users: controller for all users
    @type download_products: [ { "name": unicode, ... } ]
    @param download_products: list of configured downloadable products
    @type web_server: unicode
    @param web_server: front-end web server (determines specific support for various features)
    @rtype: Files
    @return: newly constructed Files
    """
    self.__database = database
    self.__users = users
    self.__download_products = download_products
    self.__web_server = web_server

  @expose()
  @weakly_expire
  @end_transaction
  @grab_user_id
  @validate(
    file_id = Valid_id(),
    quote_filename = Valid_bool( none_okay = True ),
    preview = Valid_bool( none_okay = True ),
    user_id = Valid_id( none_okay = True ),
  )
  def download( self, file_id, quote_filename = False, preview = True, user_id = None ):
    """
    Return the contents of file that a user has previously uploaded.

    @type file_id: unicode
    @param file_id: id of the file to download
    @type quote_filename: bool
    @param quote_filename: True to URL quote the filename of the downloaded file, False to leave it
                           as UTF-8. IE expects quoting while Firefox doesn't (optional, defaults
                           to False)
    @type preview: bool
    @param preview: True to redirect to a preview page if the file is a valid image, False to
                    unconditionally initiate a download
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: generator
    @return: file data
    @raise Access_error: the current user doesn't have access to the notebook that the file is in
    """
    db_file = self.__database.load( File, file_id )

    if not db_file or not self.__users.load_notebook( user_id, db_file.notebook_id ):
      raise Access_error()

    # if the file is openable as an image, then allow the user to view it instead of downloading it
    if preview:
      try:
        Upload_file.open_image( file_id )
        return dict( redirect = u"/files/preview?file_id=%s&quote_filename=%s" % ( file_id, quote_filename ) )
      except IOError:
        pass

    cherrypy.response.headerMap[ u"Content-Type" ] = db_file.content_type

    filename = db_file.filename.replace( '"', r"\"" ).encode( "utf8" )
    if quote_filename:
      filename = urllib.quote( filename, safe = "" )

    cherrypy.response.headerMap[ u"Content-Disposition" ] = 'attachment; filename="%s"' % filename
    cherrypy.response.headerMap[ u"Content-Length" ] = db_file.size_bytes

    if self.__web_server == u"nginx":
      cherrypy.response.headerMap[ u"X-Accel-Redirect" ] = "/download/%s" % file_id
      return ""

    def stream():
      CHUNK_SIZE = 8192
      local_file = Upload_file.open_file( file_id )
      local_file.seek(0)

      while True:
        data = local_file.read( CHUNK_SIZE )
        if len( data ) == 0: break
        yield data        

    return stream()

  @expose()
  @weakly_expire
  @end_transaction
  @validate(
    access_id = Valid_id(),
  )
  def download_product( self, access_id ):
    """
    Return the contents of downloadable product file.

    @type access_id: unicode
    @param access_id: id of download access object that grants access to the file
    @rtype: generator
    @return: file data
    @raise Access_error: the access_id is unknown or doesn't grant access to the file
    """
    # load the download_access object corresponding to the given id
    download_access = self.__database.load( Download_access, access_id )
    if download_access is None:
      raise Access_error()

    # find the product corresponding to the item_number
    products = [
      product for product in self.__download_products
      if unicode( download_access.item_number ) == product.get( u"item_number" )
    ]
    if len( products ) == 0:
      raise Access_error()

    product = products[ 0 ]

    public_filename = product[ u"filename" ].encode( "utf8" )
    local_filename = u"products/%s" % product[ u"filename" ]

    if not os.path.exists( local_filename ):
      raise Access_error()

    cherrypy.response.headerMap[ u"Content-Type" ] = u"application/octet-stream"
    cherrypy.response.headerMap[ u"Content-Disposition" ] = 'attachment; filename="%s"' % public_filename
    cherrypy.response.headerMap[ u"Content-Length" ] = os.path.getsize( local_filename )

    if self.__web_server == u"nginx":
      cherrypy.response.headerMap[ u"X-Accel-Redirect" ] = "/download_product/%s" % product[ u"filename" ]
      return ""

    def stream():
      CHUNK_SIZE = 8192
      local_file = file( local_filename, "rb" )
      local_file.seek(0)

      while True:
        data = local_file.read( CHUNK_SIZE )
        if len( data ) == 0: break
        yield data        

    return stream()

  @expose( view = File_preview_page )
  @end_transaction
  @grab_user_id
  @validate(
    file_id = Valid_id(),
    quote_filename = Valid_bool( none_okay = True ),
    user_id = Valid_id( none_okay = True ),
  )
  def preview( self, file_id, quote_filename = False, user_id = None ):
    """
    Return a page displaying an uploaded image file along with a link to download it.

    @type file_id: unicode
    @param file_id: id of the file to view
    @type quote_filename: bool
    @param quote_filename: quote_filename value to include in download URL
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: unicode
    @return: file data
    @raise Access_error: the current user doesn't have access to the notebook that the file is in
    """
    db_file = self.__database.load( File, file_id )

    if not db_file or not self.__users.load_notebook( user_id, db_file.notebook_id ):
      raise Access_error()

    filename = db_file.filename.replace( '"', r"\"" )

    return dict(
      file_id = file_id,
      filename = filename,
      quote_filename = quote_filename,
    )

  @expose()
  @weakly_expire
  @end_transaction
  @grab_user_id
  @validate(
    file_id = Valid_id(),
    max_size = Valid_int( min = 10, max = 1000, none_okay = True ),
    user_id = Valid_id( none_okay = True )
  )
  def thumbnail( self, file_id, max_size = None, user_id = None ):
    """
    Return a thumbnail for a file that a user has previously uploaded. If a thumbnail cannot be
    generated for the given file, return a default thumbnail image.

    @type file_id: unicode
    @param file_id: id of the file to return a thumbnail for
    @type max_size: int or NoneType
    @param max_size: maximum thumbnail width or height in pixels (optional, defaults to a small size)
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: generator
    @return: thumbnail image data
    @raise Access_error: the current user doesn't have access to the notebook that the file is in
    """
    db_file = self.__database.load( File, file_id )

    if not db_file or not self.__users.load_notebook( user_id, db_file.notebook_id ):
      raise Access_error()

    cherrypy.response.headerMap[ u"Content-Type" ] = u"image/png"

    DEFAULT_MAX_THUMBNAIL_SIZE = 125
    if not max_size:
      max_size = DEFAULT_MAX_THUMBNAIL_SIZE

    # attempt to open the file as an image
    image_buffer = None
    try:
      image = Upload_file.open_image( file_id )

      # scale the image down into a thumbnail
      image.thumbnail( ( max_size, max_size ), Image.ANTIALIAS )

      # save the image into a memory buffer
      image_buffer = StringIO()
      image.save( image_buffer, "PNG" )
      image_buffer.seek( 0 )
    except IOError:
      image = Image.open( "static/images/default_thumbnail.png" )
      image_buffer = StringIO()
      image.save( image_buffer, "PNG" )
      image_buffer.seek( 0 )

    return image_buffer.getvalue()

  @expose()
  @weakly_expire
  @end_transaction
  @grab_user_id
  @validate(
    file_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def image( self, file_id, user_id = None ):
    """
    Return the contents of an image file that a user has previously uploaded. This is distinct
    from the download() method above in that it doesn't set HTTP headers for a file download.

    @type file_id: unicode
    @param file_id: id of the file to return
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: generator
    @return: image data
    @raise Access_error: the current user doesn't have access to the notebook that the file is in
    """
    db_file = self.__database.load( File, file_id )

    if not db_file or not self.__users.load_notebook( user_id, db_file.notebook_id ):
      raise Access_error()

    cherrypy.response.headerMap[ u"Content-Type" ] = db_file.content_type

    if self.__web_server == u"nginx":
      cherrypy.response.headerMap[ u"X-Accel-Redirect" ] = "/download/%s" % file_id
      return ""

    def stream():
      CHUNK_SIZE = 8192
      local_file = Upload_file.open_file( file_id )
      local_file.seek(0)

      while True:
        data = local_file.read( CHUNK_SIZE )
        if len( data ) == 0: break
        yield data        

    return stream()

  @expose( view = Json )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id( none_okay = True ),
    user_id = Valid_id( none_okay = True ),
  )
  def upload_id( self, notebook_id, note_id, user_id ):
    """
    Generate and return a unique file id for use in an upload.

    @type notebook_id: unicode
    @param notebook_id: id of the notebook that the upload will be to
    @type note_id: unicode
    @param note_id: id of the note that the upload will be to
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: unicode
    @return: { 'file_id': file_id }
    @raise Access_error: the current user doesn't have access to the given notebook
    """
    notebook = self.__users.load_notebook( user_id, notebook_id, read_write = True, note_id = note_id )

    if not notebook or notebook.read_write == Notebook.READ_WRITE_FOR_OWN_NOTES:
      raise Access_error()

    file_id = self.__database.next_id( File )

    return dict(
      file_id = file_id,
    )

  @expose( view = Blank_page )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    upload = (),
    notebook_id = Valid_id(),
    note_id = Valid_id( none_okay = True ),
    file_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def upload( self, upload, notebook_id, note_id, file_id, user_id ):
    """
    Upload a file from the client for attachment to a particular note. The file_id must be provided
    as part of the query string, even if the other values are submitted as form data.

    @type upload: cgi.FieldStorage
    @param upload: file handle to uploaded file
    @type notebook_id: unicode
    @param notebook_id: id of the notebook that the upload is to
    @type note_id: unicode or NoneType
    @param note_id: id of the note that the upload is to (if any)
    @type file_id: unicode
    @param file_id: id of the file being uploaded
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: unicode
    @return: rendered HTML page
    @raise Access_error: the current user doesn't have access to the given notebook or note
    @raise Upload_error: the Content-Length header value is invalid
    """
    global current_uploads, current_uploads_lock

    current_uploads_lock.acquire()
    try:
      uploaded_file = current_uploads.get( file_id )
      if not uploaded_file:
        return dict( script = general_error_script % u"Please select a file to upload." )

      del( current_uploads[ file_id ] )
    finally:
      current_uploads_lock.release()

    user = self.__database.load( User, user_id )
    notebook = self.__users.load_notebook( user_id, notebook_id, read_write = True )

    if not user or not notebook or notebook.read_write == Notebook.READ_WRITE_FOR_OWN_NOTES:
      uploaded_file.delete()
      return dict( script = general_error_script % u"Sorry, you don't have access to do that. Please make sure you're logged in as the correct user." )

    content_type = upload.headers.get( "content-type" )

    # if we didn't receive all of the expected data, abort
    if uploaded_file.total_received_bytes < uploaded_file.content_length:
      uploaded_file.delete()
      return dict( script = general_error_script % u"The uploaded file was not fully received. Please try again or contact support." )

    if uploaded_file.file_received_bytes == 0:
      uploaded_file.delete()
      return dict( script = general_error_script % u"The uploaded file was not received. Please make sure that the file exists." )

    # if the uploaded file's size would put the user over quota, bail and inform the user
    rate_plan = self.__users.rate_plan( user.rate_plan )
    storage_quota_bytes = rate_plan.get( u"storage_quota_bytes" )

    if storage_quota_bytes and user.storage_bytes + uploaded_file.total_received_bytes > storage_quota_bytes:
      uploaded_file.delete()
      return dict( script = quota_error_script )

    # record metadata on the upload in the database
    db_file = File.create( file_id, notebook_id, note_id, uploaded_file.filename, uploaded_file.file_received_bytes, content_type )
    self.__database.save( db_file, commit = False )
    self.__users.update_storage( user_id, commit = False )
    self.__database.commit()
    uploaded_file.close()

    return dict()

  @expose( view = Json )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    file_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def progress( self, file_id, user_id = None ):
    """
    Return information on a file that is in the process of being uploaded. This method does not
    perform any access checks, but the only information revealed is the file's upload progress.

    This method is intended to be polled while the file is uploading, and its returned data is
    intended to mimic the API described here:
    http://wiki.nginx.org//NginxHttpUploadProgressModule

    @type file_id: unicode
    @param file_id: id of a currently uploading file
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: dict
    @return: one of the following:
      { 'state': 'starting' }                          // file_id is unknown
      { 'state': 'done' }                              // upload is complete
      { 'state': 'error', 'status': http_error_code }  // upload generated an HTTP error
      { 'state': 'uploading',                          // upload is in progress
        'received': bytes_received, 'size': total_bytes }
    """
    global current_uploads

    uploading_file = current_uploads.get( file_id )
    db_file = None

    if uploading_file:
      # if the uploaded file's size would put the user over quota, bail and inform the user
      SOFT_QUOTA_FACTOR = 1.05 # fudge factor since content_length isn't really the file's actual size

      user = self.__database.load( User, user_id )
      if not user:
        return dict(
          state = "error",
          stauts = httplib.FORBIDDEN,
        )

      rate_plan = self.__users.rate_plan( user.rate_plan )

      storage_quota_bytes = rate_plan.get( u"storage_quota_bytes" )
      if storage_quota_bytes and \
         user.storage_bytes + uploading_file.content_length > storage_quota_bytes * SOFT_QUOTA_FACTOR:
        return dict(
          state = "error",
          stauts = httplib.REQUEST_ENTITY_TOO_LARGE,
        )

      return dict(
        state = u"uploading",
        received = uploading_file.total_received_bytes,
        size = uploading_file.content_length,
      );

    db_file = self.__database.load( File, file_id )
    if not db_file:
      return dict(
        state = "error",
        stauts = httplib.NOT_FOUND,
      )

    if db_file.filename is None:
      return dict( state = u"starting" );

    # the file is completely uploaded (in the database with a filename)
    return dict( state = u"done" );

  @expose( view = Json )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    file_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def stats( self, file_id, user_id = None ):
    """
    Return information on a file that has been completely uploaded with its metadata stored in the
    database. Also return the user's current storage utilization in bytes.

    @type file_id: unicode
    @param file_id: id of the file to report on
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: dict
    @return: {
      'filename': filename,
      'size_bytes': filesize,
      'storage_bytes': current storage usage by user
    }
    @raise Access_error: the current user doesn't have access to the notebook that the file is in
    """
    db_file = self.__database.load( File, file_id )
    if db_file is None:
      raise Access_error()

    db_notebook = self.__users.load_notebook( user_id, db_file.notebook_id )
    if db_notebook is None or db_notebook.read_write == Notebook.READ_WRITE_FOR_OWN_NOTES:
      raise Access_error()

    user = self.__database.load( User, user_id )
    if not user:
      raise Access_error()

    user.group_storage_bytes = self.__users.calculate_group_storage( user )

    return dict(
      filename = db_file.filename,
      size_bytes = db_file.size_bytes,
      storage_bytes = user.storage_bytes,
    )

  @expose( view = Json )
  @end_transaction
  @grab_user_id
  @validate(
    file_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def delete( self, file_id, user_id = None ):
    """
    Delete a file that has been completely uploaded, removing both its metadata from the database
    and its data from the filesystem. Return the user's current storage utilization in bytes.

    @type file_id: unicode
    @param file_id: id of the file to delete
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: dict
    @return: {
      'storage_bytes': current storage usage by user
    }
    @raise Access_error: the current user doesn't have access to the notebook that the file is in
    """
    db_file = self.__database.load( File, file_id )
    if db_file is None:
      raise Access_error()

    db_notebook = self.__users.load_notebook( user_id, db_file.notebook_id, read_write = True )
    if db_notebook is None or db_notebook.read_write == Notebook.READ_WRITE_FOR_OWN_NOTES:
      raise Access_error()

    self.__database.execute( db_file.sql_delete(), commit = False )
    user = self.__users.update_storage( user_id, commit = False )
    self.__database.uncache( db_file )
    self.__database.commit()
    user.group_storage_bytes = self.__users.calculate_group_storage( user )

    Upload_file.delete_file( file_id )

    return dict(
      storage_bytes = user.storage_bytes,
    )

  @expose( view = Json )
  @end_transaction
  @grab_user_id
  @validate(
    file_id = Valid_id(),
    filename = unicode,
    user_id = Valid_id( none_okay = True ),
  )
  def rename( self, file_id, filename, user_id = None ):
    """
    Rename a file that has been completely uploaded.

    @type file_id: unicode
    @param file_id: id of the file to delete
    @type filename: unicode
    @param filename: new name for the file
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: dict
    @return: {}
    @raise Access_error: the current user doesn't have access to the notebook that the file is in
    """
    db_file = self.__database.load( File, file_id )
    if db_file is None:
      raise Access_error()

    db_notebook = self.__users.load_notebook( user_id, db_file.notebook_id, read_write = True )
    if db_notebook is None or db_notebook.read_write == Notebook.READ_WRITE_FOR_OWN_NOTES:
      raise Access_error()

    db_file.filename = filename
    self.__database.save( db_file )

    return dict()

  def parse_csv( self, file_id, skip_header = False ):
    """
    Attempt to parse a previously uploaded file as a table or spreadsheet. Generate rows as they're
    requested.

    @type file_id: unicode
    @param file_id: id of the file to parse
    @type skip_header: bool
    @param skip_header: if a line of header labels is detected, don't include it in the generated
                        rows (defaults to False)
    @rtype: generator
    @return: rows of data from the parsed file. each row is a list of elements
    @raise Parse_error: there was an error in parsing the given file
    """
    APPROX_SNIFF_SAMPLE_SIZE_BYTES = 1024 * 50

    try:
      import csv

      table_file = Upload_file.open_file( file_id )
      table_file.seek( 0 ) # necessary in case the file is opened by another call to parse_csv()
      sniffer = csv.Sniffer()

      # attempt to determine the presence of a header
      lines = table_file.readlines( APPROX_SNIFF_SAMPLE_SIZE_BYTES )
      sniff_sample = "".join( lines )

      has_header = sniffer.has_header( sniff_sample )

      # attempt to determine the file's character encoding
      detector = UniversalDetector()
      for line in lines:
        detector.feed( line )
        if detector.done: break

      detector.close()
      encoding = detector.result.get( "encoding" )

      table_file.seek( 0 )
      reader = csv.reader( table_file )

      # skip the header if requested to do so
      if has_header and skip_header:
        reader.next()

      expected_row_length = None

      for row in reader:
        # all rows must have the same number of elements
        current_row_length = len( row )
        if current_row_length == 0:
          continue

        if expected_row_length and current_row_length != expected_row_length:
          raise Parse_error()
        else:
          expected_row_length = current_row_length

        yield [ element.decode( encoding ) for element in row ]
    except ( csv.Error, IOError, TypeError ):
      raise Parse_error()

  @expose( view = Json )
  @end_transaction
  @grab_user_id
  @validate(
    file_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def csv_head( self, file_id, user_id = None ):
    """
    Attempt to parse a previously uploaded file as a table or spreadsheet. Return the first few rows
    of that table, with each element truncated to a maximum length if necessary.

    Currently, only a CSV file format is supported.

    @type file_id: unicode
    @param file_id: id of the file to parse
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: dict
    @return: {
      'file_id': file id,
      'rows': list of parsed rows, each of which is a list of elements,
    }
    @raise Access_error: the current user doesn't have access to the notebook that the file is in
    @raise Parse_error: there was an error in parsing the given file
    """
    MAX_ROW_COUNT = 4
    MAX_ELEMENT_LENGTH = 30
    MAX_ROW_ELEMENT_COUNT = 20

    db_file = self.__database.load( File, file_id )
    if db_file is None:
      raise Access_error()

    db_notebook = self.__users.load_notebook( user_id, db_file.notebook_id )
    if db_notebook is None or db_notebook.read_write == Notebook.READ_WRITE_FOR_OWN_NOTES:
      raise Access_error()

    parser = self.parse_csv( file_id )
    rows = []

    def truncate( element ):
      if len( element ) > MAX_ELEMENT_LENGTH:
        return "%s ..." % element[ : MAX_ELEMENT_LENGTH ]

      return element

    for row in parser:
      if len( row ) == 0:
        continue

      rows.append( [ truncate( element ) for element in row ][ : MAX_ROW_ELEMENT_COUNT ] )
      if len( rows ) == MAX_ROW_COUNT:
        break

    if len( rows ) == 0:
      raise Parse_error()

    return dict(
      file_id = file_id,
      rows = rows,
    )

  def purge_unused( self, note, purge_all_links = False ):
    """
    Delete files that were linked from the given note but no longer are.

    @type note: model.Note
    @param note: note to search for file links
    @type purge_all_links: bool
    @param purge_all_links: if True, delete all files that are/were linked from this note
    """
    # load metadata for all files with the given note's note_id 
    files = self.__database.select_many( File, File.sql_load_note_files( note.object_id ) )
    files_to_delete = dict( [ ( db_file.object_id, db_file ) for db_file in files ] )

    # search through the note's contents for current links to files
    if purge_all_links is False:
      for match in self.FILE_LINK_PATTERN.finditer( note.contents ):
        file_id = match.groups( 0 )[ 0 ]

        # we've found a link for file_id, so don't delete that file
        files_to_delete.pop( file_id, None )

    # for each file to delete, delete its metadata from the database and its data from the
    # filesystem
    for ( file_id, db_file ) in files_to_delete.items():
      self.__database.execute( db_file.sql_delete(), commit = False )
      self.__database.uncache( db_file )
      Upload_file.delete_file( file_id )

    self.__database.commit()
