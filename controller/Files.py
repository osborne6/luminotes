import os
import re
import cgi
import time
import urllib
import tempfile
import cherrypy
from PIL import Image
from cStringIO import StringIO
from threading import Lock, Event
from Expose import expose
from Validate import validate, Valid_int, Valid_bool, Validation_error
from Database import Valid_id, end_transaction
from Users import grab_user_id, Access_error
from Expire import strongly_expire
from model.File import File
from model.User import User
from view.Upload_page import Upload_page
from view.Blank_page import Blank_page
from view.Json import Json
from view.Progress_bar import stream_progress, stream_quota_error, quota_error_script, general_error_script
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


# map of upload id to Upload_file
current_uploads = {}
current_uploads_lock = Lock()


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
    self.__total_received_bytes_updated = Event()
    self.__complete = Event()
  
  def write( self, data ):
    self.__file.write( data )
    self.__file_received_bytes += len( data )
    self.__total_received_bytes = cherrypy.request.rfile.bytes_read
    self.__total_received_bytes_updated.set()

  def tell( self ):
    return self.__file.tell()

  def seek( self, position ):
    self.__file.seek( position )

  def read( self, size = None ):
    if size is None:
      return self.__file.read()

    return self.__file.read( size )

  def wait_for_total_received_bytes( self ):
    self.__total_received_bytes_updated.wait( timeout = cherrypy.server.socket_timeout )
    self.__total_received_bytes_updated.clear()
    return self.__total_received_bytes

  def close( self ):
    self.__file.close()
    self.complete()

  def complete( self ):
    self.__complete.set()

  def delete( self ):
    self.__file.close()
    self.delete_file( self.__file_id )

  def wait_for_complete( self ):
    self.__complete.wait( timeout = cherrypy.server.socket_timeout )

  @staticmethod
  def make_server_filename( file_id ):
    return u"files/%s" % file_id

  @staticmethod
  def open_file( file_id, mode = None ):
    if mode:
      return file( Upload_file.make_server_filename( file_id ), mode )
    return file( Upload_file.make_server_filename( file_id ) )

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
  object, we can track its progress as its written. Inspired by:
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

    # release the cherrypy session lock so that the user can issue other commands while the file is
    # uploading
    try:
      cherrypy.session.release_lock()
    except KeyError:
      pass

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
  FILE_LINK_PATTERN = re.compile( u'<a\s+href="[^"]*/files/download\?file_id=([^"&]+)(&[^"]*)?">(<img )?[^<]+</a>', re.IGNORECASE )

  """
  Controller for dealing with uploaded files, corresponding to the "/files" URL.
  """
  def __init__( self, database, users ):
    """
    Create a new Files object.

    @type database: controller.Database
    @param database: database that file metadata is stored in
    @type users: controller.Users
    @param users: controller for all users
    @rtype: Files
    @return: newly constructed Files
    """
    self.__database = database
    self.__users = users

  @expose()
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
    # release the session lock before beginning to stream the download. otherwise, if the
    # download is cancelled before it's done, the lock won't be released
    try:
      cherrypy.session.release_lock()
    except KeyError:
      pass

    db_file = self.__database.load( File, file_id )

    if not db_file or not self.__users.check_access( user_id, db_file.notebook_id ):
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

    def stream():
      CHUNK_SIZE = 8192
      local_file = Upload_file.open_file( file_id )

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

    if not db_file or not self.__users.check_access( user_id, db_file.notebook_id ):
      raise Access_error()

    filename = db_file.filename.replace( '"', r"\"" ).encode( "utf8" )

    return dict(
      file_id = file_id,
      filename = filename,
      quote_filename = quote_filename,
    )

  @expose()
  @end_transaction
  @grab_user_id
  @validate(
    file_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def thumbnail( self, file_id, user_id = None ):
    """
    Return a thumbnail for a file that a user has previously uploaded. If a thumbnail cannot be
    generated for the given file, return a default thumbnail image.

    @type file_id: unicode
    @param file_id: id of the file to return a thumbnail for
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: generator
    @return: thumbnail image data
    @raise Access_error: the current user doesn't have access to the notebook that the file is in
    """
    try:
      cherrypy.session.release_lock()
    except KeyError:
      pass

    db_file = self.__database.load( File, file_id )

    if not db_file or not self.__users.check_access( user_id, db_file.notebook_id ):
      raise Access_error()

    cherrypy.response.headerMap[ u"Content-Type" ] = u"image/png"

    # attempt to open the file as an image
    image_buffer = None
    try:
      image = Upload_file.open_image( file_id )

      # scale the image down into a thumbnail
      THUMBNAIL_MAX_SIZE = ( 125, 125 ) # in pixels
      image.thumbnail( THUMBNAIL_MAX_SIZE, Image.ANTIALIAS )

      # save the image into a memory buffer
      image_buffer = StringIO()
      image.save( image_buffer, "PNG" )
      image_buffer.seek( 0 )
    except IOError:
      image = Image.open( "static/images/default_thumbnail.png" )
      image_buffer = StringIO()
      image.save( image_buffer, "PNG" )
      image_buffer.seek( 0 )

    def stream( image_buffer ):
      CHUNK_SIZE = 8192

      while True:
        data = image_buffer.read( CHUNK_SIZE )
        if len( data ) == 0: break
        yield data        

    return stream( image_buffer )

  @expose()
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
    try:
      cherrypy.session.release_lock()
    except KeyError:
      pass

    db_file = self.__database.load( File, file_id )

    if not db_file or not self.__users.check_access( user_id, db_file.notebook_id ):
      raise Access_error()

    cherrypy.response.headerMap[ u"Content-Type" ] = db_file.content_type

    def stream():
      CHUNK_SIZE = 8192
      local_file = Upload_file.open_file( file_id )

      while True:
        data = local_file.read( CHUNK_SIZE )
        if len( data ) == 0: break
        yield data        

    return stream()

  @expose( view = Upload_page )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def upload_page( self, notebook_id, note_id, user_id ):
    """
    Provide the information necessary to display the file upload page, including the generation of a
    unique file id.

    @type notebook_id: unicode
    @param notebook_id: id of the notebook that the upload will be to
    @type note_id: unicode
    @param note_id: id of the note that the upload will be to
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: unicode
    @return: rendered HTML page
    @raise Access_error: the current user doesn't have access to the given notebook
    """
    if not self.__users.check_access( user_id, notebook_id, read_write = True ):
      raise Access_error()

    file_id = self.__database.next_id( File )

    return dict(
      notebook_id = notebook_id,
      note_id = note_id,
      file_id = file_id,
    )

  @expose( view = Blank_page )
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    upload = (),
    notebook_id = Valid_id(),
    note_id = Valid_id(),
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
    @type note_id: unicode
    @param note_id: id of the note that the upload is to
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
    if not user or not self.__users.check_access( user_id, notebook_id, read_write = True ):
      uploaded_file.delete()
      return dict( script = general_error_script % u"Sorry, you don't have access to do that. Please make sure you're logged in as the correct user." )

    content_type = upload.headers.get( "content-type" )

    # if we didn't receive all of the expected data, abort
    if uploaded_file.total_received_bytes < uploaded_file.content_length:
      uploaded_file.delete()
      return dict() # hopefully, the call to progress() will report this to the user

    # if the uploaded file's size would put the user over quota, bail and inform the user
    rate_plan = self.__users.rate_plan( user.rate_plan )
    if user.storage_bytes + uploaded_file.total_received_bytes > rate_plan.get( u"storage_quota_bytes", 0 ):
      uploaded_file.delete()
      return dict( script = quota_error_script )

    # record metadata on the upload in the database
    db_file = File.create( file_id, notebook_id, note_id, uploaded_file.filename, uploaded_file.file_received_bytes, content_type )
    self.__database.save( db_file, commit = False )
    self.__users.update_storage( user_id, commit = False )
    self.__database.commit()
    uploaded_file.close()

    return dict()

  @expose()
  @strongly_expire
  @end_transaction
  @grab_user_id
  @validate(
    file_id = Valid_id(),
    filename = unicode,
    user_id = Valid_id( none_okay = True ),
  )
  def progress( self, file_id, filename, user_id = None ):
    """
    Stream information on a file that is in the process of being uploaded. This method does not
    perform any access checks, but the only information streamed is a progress bar and upload
    percentage.

    @type file_id: unicode
    @param file_id: id of a currently uploading file
    @type filename: unicode
    @param filename: name of the file to report on
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: unicode
    @return: streaming HTML progress bar
    """
    global current_uploads

    # release the session lock before beginning to stream the upload report. otherwise, if the
    # upload is cancelled before it's done, the lock won't be released
    try:
      cherrypy.session.release_lock()
    except KeyError:
      pass

    # poll until the file is uploading (as determined by current_uploads) or completely uploaded (in
    # the database with a filename)
    while True:
      uploading_file = current_uploads.get( file_id )
      db_file = None

      if uploading_file:
        fraction_reported = 0.0
        break

      db_file = self.__database.load( File, file_id )
      if not db_file:
        raise Upload_error( u"The file id is unknown" )
      if db_file.filename is None:
        time.sleep( 0.1 )
        continue
      fraction_reported = 1.0
      break

    # if the uploaded file's size would put the user over quota, bail and inform the user
    if uploading_file:
      SOFT_QUOTA_FACTOR = 1.05 # fudge factor since content_length isn't really the file's actual size

      user = self.__database.load( User, user_id )
      if not user:
        raise Access_error()

      rate_plan = self.__users.rate_plan( user.rate_plan )

      if user.storage_bytes + uploading_file.content_length > rate_plan.get( u"storage_quota_bytes", 0 ) * SOFT_QUOTA_FACTOR:
        return stream_quota_error()

    return stream_progress( uploading_file, filename, fraction_reported )

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

    if not db_file or not self.__users.check_access( user_id, db_file.notebook_id ):
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

    if not db_file or not self.__users.check_access( user_id, db_file.notebook_id, read_write = True ):
      raise Access_error()

    self.__database.execute( db_file.sql_delete(), commit = False )
    user = self.__users.update_storage( user_id, commit = False )
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

    if not db_file or not self.__users.check_access( user_id, db_file.notebook_id, read_write = True ):
      raise Access_error()

    db_file.filename = filename
    self.__database.save( db_file )

    return dict()

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
      Upload_file.delete_file( file_id )

    self.__database.commit()
