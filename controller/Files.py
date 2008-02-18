import cgi
import time
import tempfile
import cherrypy
from threading import Lock, Event
from Expose import expose
from Validate import validate, Valid_int, Validation_error
from Database import Valid_id
from Users import grab_user_id
from Expire import strongly_expire
from model.File import File
from view.Upload_page import Upload_page
from view.Blank_page import Blank_page
from view.Json import Json


class Access_error( Exception ):
  def __init__( self, message = None ):
    if message is None:
      message = u"Sorry, you don't have access to do that. Please make sure you're logged in as the correct user."

    Exception.__init__( self, message )
    self.__message = message

  def to_dict( self ):
    return dict(
      error = self.__message
    )


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
    self.__file = file( self.make_server_filename( file_id ), "w+" )
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
    self.__complete.set()

  def wait_for_complete( self ):
    self.__complete.wait( timeout = cherrypy.server.socket_timeout )

  @staticmethod
  def make_server_filename( file_id ):
    return u"files/%s" % file_id

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
  @type user_id: unicode or NoneType
  @param user_id: id of current logged-in user (if any)
  @rtype: Upload_file
  @return: wrapped temporary file used to store the upload
  @raise Upload_error: the provided file_id value is invalid, or the filename or Content-Length is
                       missing
  """
  def make_file( self, binary = None, user_id = None ):
    global current_uploads, current_uploads_lock

    cherrypy.server.max_request_body_size = 0 # remove CherryPy default file size limit of 100 MB
    cherrypy.response.timeout = 3600 * 2 # increase upload timeout to 2 hours (default is 5 min)
    cherrypy.server.socket_timeout = 60 # increase socket timeout to one minute (default is 10 sec)
    DASHES_AND_NEWLINES = 6 # four dashes and two newlines

    # release the cherrypy session lock so that the user can issue other commands while the file is
    # uploading
    cherrypy.session.release_lock()

    # pluck the file id out of the query string. it would be preferable to grab it out of parsed
    # form variables instead, but at this point in the processing, all the form variables might not
    # be parsed
    file_id = cgi.parse_qs( cherrypy.request.query_string ).get( u"file_id", [ None ] )[ 0 ]
    try:
      file_id = Valid_id()( file_id )
    except ValueError:
      raise Upload_error( "The file_id is invalid." )

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
    # TODO: verify that the uploaded file is always sent as the last parameter
    existing_file = current_uploads.get( file_id )
    if existing_file:
      existing_file.close()

    upload_file = Upload_file( file_id, self.filename.strip(), content_length )

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
  """
  Controller for dealing with uploaded files, corresponding to the "/files" URL.
  """
  def __init__( self, database, users ):
    """
    Create a new Files object.

    @type database: controller.Database
    @param database: database that files are stored in
    @type users: controller.Users
    @param users: controller for all users
    @rtype: Files
    @return: newly constructed Files
    """
    self.__database = database
    self.__users = users

  @expose()
  @grab_user_id
  @validate(
    file_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def download( self, file_id, user_id = None ):
    """
    Return the contents of file that a user has previously uploaded.

    @type file_id: unicode
    @param file_id: id of the file to download
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: unicode
    @return: file data
    @raise Access_error: the current user doesn't have access to the notebook that the file is in
    """
    db_file = self.__database.load( File, file_id )

    if not db_file or not self.__users.check_access( user_id, db_file.notebook_id ):
      raise Access_error()

    db_file = self.__database.load( File, file_id )

    cherrypy.response.headerMap[ u"Content-Disposition" ] = u"attachment; filename=%s" % db_file.filename
    cherrypy.response.headerMap[ u"Content-Length" ] = db_file.size_bytes
    cherrypy.response.headerMap[ u"Content-Type" ] = db_file.content_type

    def stream():
      CHUNK_SIZE = 8192
      local_file = file( Upload_file.make_server_filename( file_id ) )

      while True:
        data = local_file.read( CHUNK_SIZE )
        if len( data ) == 0: break
        yield data        

    return stream()


  @expose( view = Upload_page )
  @strongly_expire
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

    if not self.__users.check_access( user_id, notebook_id, read_write = True ):
      raise Access_error()

    # write the file to the database
    uploaded_file = current_uploads.get( file_id )
    if not uploaded_file:
      raise Upload_error()

    content_type = upload.headers.get( "content-type" )

# TODO: somehow detect when upload is canceled and abort

    db_file = File.create( file_id, notebook_id, note_id, uploaded_file.filename, uploaded_file.file_received_bytes, content_type )
    self.__database.save( db_file )
    uploaded_file.close()

    current_uploads_lock.acquire()
    try:
      del( current_uploads[ file_id ] )
    finally:
      current_uploads_lock.release()

    return dict()

  @expose()
  @strongly_expire
  @validate(
    file_id = Valid_id(),
    filename = unicode,
  )
  def progress( self, file_id, filename ):
    """
    Stream information on a file that is in the process of being uploaded. This method does not
    perform any access checks, but the only information streamed is a progress bar and upload
    percentage.

    @type file_id: unicode
    @param file_id: id of a currently uploading file
    @type filename: unicode
    @param filename: name of the file to report on
    @rtype: unicode
    @return: streaming HTML progress bar
    """
    # release the session lock before beginning to stream the upload report. otherwise, if the
    # upload is cancelled before it's done, the lock won't be released
    cherrypy.session.release_lock()

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

    # TODO: maybe move this to the view/ directory
    def report( uploading_file, fraction_reported ):
      """
      Stream a progress meter as it uploads.
      """
      progress_bytes = 0
      progress_width_em = 20
      tick_increment = 0.01
      progress_bar = u'<img src="/static/images/tick.png" style="width: %sem; height: 1em;" id="progress_bar" />' % \
        ( progress_width_em * tick_increment )

      yield \
        u"""
        <html>
        <head>
          <link href="/static/css/upload.css" type="text/css" rel="stylesheet" />
          <script type="text/javascript" src="/static/js/MochiKit.js"></script>
          <meta content="text/html; charset=UTF-8" http_equiv="content-type" />
        </head>
        <body>
        """

      base_filename = filename.split( u"/" )[ -1 ].split( u"\\" )[ -1 ]
      yield \
        u"""
        <div class="field_label">uploading %s: </div>
        <table><tr>
        <td><div id="progress_border">
        %s
        </div></td>
        <td></td>
        <td><span id="status"></span></td>
        <td></td>
        <td><input type="submit" id="cancel_button" class="button" value="cancel" onclick="withDocument( window.parent.document, function () { getElement( 'upload_frame' ).pulldown.shutdown(); } );" /></td>
        </tr></table>
        <script type="text/javascript">
        function tick( fraction ) {
          setElementDimensions(
            "progress_bar",
            { "w": %s * fraction }, "em"
          );
          if ( fraction >= 1.0 )
            replaceChildNodes( "status", "100%%" );
          else
            replaceChildNodes( "status", Math.floor( fraction * 100.0 ) + "%%" );
        }
        </script>
        """ % ( cgi.escape( base_filename ), progress_bar, progress_width_em )

      if uploading_file:
        received_bytes = 0
        while received_bytes < uploading_file.content_length:
          received_bytes = uploading_file.wait_for_total_received_bytes()
          fraction_done = float( received_bytes ) / float( uploading_file.content_length )

          if fraction_done == 1.0 or fraction_done > fraction_reported + tick_increment:
            fraction_reported = fraction_done
            yield '<script type="text/javascript">tick(%s);</script>' % fraction_reported

        uploading_file.wait_for_complete()

      if fraction_reported < 1.0:
        yield "An error occurred when uploading the file.</body></html>"
        return

      yield \
        u"""
        <script type="text/javascript">
        withDocument( window.parent.document, function () { getElement( "upload_frame" ).pulldown.upload_complete(); } );
        </script>
        </body>
        </html>
        """

    return report( uploading_file, fraction_reported )

  @expose( view = Json )
  @strongly_expire
  @grab_user_id
  @validate(
    file_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def stats( self, file_id, user_id = None ):
    """
    Return information on a file that has been completely uploaded and is stored in the database.

    @type file_id: unicode
    @param file_id: id of the file to report on
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: dict
    @return: {
      'filename': filename,
      'size_bytes': filesize,
    }
    @raise Access_error: the current user doesn't have access to the notebook that the file is in
    """
    db_file = self.__database.load( File, file_id )

    if not db_file or not self.__users.check_access( user_id, db_file.notebook_id ):
      raise Access_error()

    return dict(
      filename = db_file.filename,
      size_bytes = db_file.size_bytes,
    )

  def rename( file_id, filename ):
    pass # TODO
