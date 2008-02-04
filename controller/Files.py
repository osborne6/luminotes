import cgi
import cherrypy
from Expose import expose
from Validate import validate
from Database import Valid_id
from Users import grab_user_id
from Expire import strongly_expire
from view.Upload_page import Upload_page


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

  @expose( view = Upload_page )
  @validate(
    notebook_id = Valid_id(),
    note_id = Valid_id(),
  )
  def upload_page( self, notebook_id, note_id ):
    """
    Provide the information necessary to display the file upload page.

    @type notebook_id: unicode
    @param notebook_id: id of the notebook that the upload will be to
    @type note_id: unicode
    @param note_id: id of the note that the upload will be to
    @rtype: unicode
    @return: rendered HTML page
    """
    return dict(
      notebook_id = notebook_id,
      note_id = note_id,
    )

  @expose()
  @strongly_expire
  @grab_user_id
  @validate(
    upload = (),
    notebook_id = Valid_id(),
    note_id = Valid_id(),
    user_id = Valid_id( none_okay = True ),
  )
  def upload_file( self, upload, notebook_id, note_id, user_id ):
    """
    Upload a file from the client for attachment to a particular note.

    @type upload: cgi.FieldStorage
    @param upload: file handle to uploaded file
    @type notebook_id: unicode
    @param notebook_id: id of the notebook that the upload is to
    @type note_id: unicode
    @param note_id: id of the note that the upload is to
    @raise Access_error: the current user doesn't have access to the given notebook or note
    @raise Upload_error: an error occurred when processing the uploaded file
    @type user_id: unicode or NoneType
    @param user_id: id of current logged-in user (if any)
    @rtype: unicode
    @return: rendered HTML page
    """
    if not self.__users.check_access( user_id, notebook_id ):
      raise Access_error()

    cherrypy.server.max_request_body_size = 0 # remove file size limit of 100 MB
    cherrypy.response.timeout = 3600    # increase upload timeout to one hour (default is 5 min)
    cherrypy.server.socket_timeout = 60 # increase socket timeout to one minute (default is 10 sec)
    # TODO: increase to 8k
    CHUNK_SIZE = 1#8 * 1024 # 8 Kb

    headers = {}
    for key, val in cherrypy.request.headers.iteritems():
      headers[ key.lower() ] = val

    try:
      file_size = int( headers.get( "content-length", 0 ) )
    except ValueError:
      raise Upload_error()
    if file_size <= 0:
      raise Upload_error()

    filename = upload.filename.strip()

    def process_upload():
      """
      Process the file upload while streaming a progress meter as it uploads.
      """
      progress_bytes = 0
      fraction_reported = 0.0
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

      if not filename:
        yield \
          u"""
          <div class="field_label">upload error: </div>
          Please check that the filename is valid.
          """
        return

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

      while True:
        chunk = upload.file.read( CHUNK_SIZE )
        if not chunk: break
        progress_bytes += len( chunk )
        fraction_done = float( progress_bytes ) / float( file_size )

        if fraction_done > fraction_reported + tick_increment:
          yield '<script type="text/javascript">tick(%s);</script>' % fraction_reported
          fraction_reported += tick_increment
          import time
          time.sleep(0.05) # TODO: removeme

        # TODO: write to the database

      if fraction_reported == 0:
        yield "An error occurred when uploading the file."
        return

      # the file finished uploading, so fill out the progress meter to 100%
      if fraction_reported < 1.0:
        yield '<script type="text/javascript">tick(1.0);</script>'

      yield \
        u"""
        </body>
        </html>
        """

      upload.file.close()
      cherrypy.request.rfile.close()

    # release the session lock before beginning the upload, because if the upload is cancelled
    # before it's done, the lock won't be released
    cherrypy.session.release_lock()

    return process_upload()
