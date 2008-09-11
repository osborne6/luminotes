import smtplib
import cherrypy
from pysqlite2 import dbapi2 as sqlite
from controller.Database import Database, Connection_wrapper
from Stub_cache import Stub_cache
from Stub_view import Stub_view
from Stub_smtp import Stub_smtp
from config import Common
from datetime import datetime
from StringIO import StringIO
from copy import copy


class Wrapped_StringIO( StringIO ):
  """
  A wrapper for StringIO that includes a bytes_read property, needed to work with
  controller.Files.Upload_file.
  """
  bytes_read = property( lambda self: self.tell() )


class Truncated_StringIO( Wrapped_StringIO ):
  """
  A wrapper for Wrapped_StringIO that forcibly closes the file when only some of it has been read.
  Used for simulating an upload that is canceled part of the way through.
  """
  def readline( self, size = None ):
    if self.tell() >= len( self.getvalue() ) * 0.25:
      self.close()
      return ""

    return Wrapped_StringIO.readline( self, 256 )


class Test_controller( object ):
  def __init__( self ):
    from model.User import User
    from model.Group import Group
    from model.Notebook import Notebook
    from model.Note import Note
    from model.Invite import Invite
    from model.User_revision import User_revision
    from model.File import File

  def setUp( self ):
    # trick tested methods into using a fake SMTP server
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    from controller.Root import Root
    cherrypy.lowercase_api = True
    self.database = Database(
      Connection_wrapper( sqlite.connect( ":memory:", detect_types = sqlite.PARSE_DECLTYPES, check_same_thread = False ) ),
      cache = Stub_cache(),
    )
    self.database.execute_script( file( "model/schema.sqlite" ).read(), commit = True )

    self.settings = {
      u"global": {
        u"server.environment": "production",
        u"session_filter.on": True,
        u"session_filter.storage_type": u"ram",
        u"session_filter.locking": "implicit",
        u"encoding_filter.on": True,
        u"encoding_filter.encoding": "utf-8",
        u"decoding_filter.on": True,
        u"decoding_filter.encoding": "utf-8",
        u"server.log_to_screen": False,
        u"luminotes.http_url" : u"http://luminotes.com",
        u"luminotes.https_url" : u"https://luminotes.com",
        u"luminotes.http_proxy_ip" : u"127.0.0.1",
        u"luminotes.https_proxy_ip" : u"127.0.0.2",
        u"luminotes.support_email": "unittest@luminotes.com",
        u"luminotes.payment_email": "unittest@luminotes.com",
        u"luminotes.rate_plans": [
          {
            u"name": u"super",
            u"storage_quota_bytes": 1337 * 10,
            u"notebook_collaboration": False,
            u"user_admin": False,
            u"included_users": 1,
            u"fee": 1.99,
            u"yearly_fee": 19.90,
            u"button": u"[subscribe here user %s!] button",
            u"yearly_button": u"[yearly subscribe here user %s!] button",
          },
          {
            u"name": "extra super",
            u"storage_quota_bytes": 31337 * 1000,
            u"notebook_collaboration": True,
            u"user_admin": True,
            u"included_users": 3,
            u"fee": 9.00,
            u"yearly_fee": 90.00,
            u"button": u"[or here user %s!] button",
            u"yearly_button": u"[yearly or here user %s!] button",
          },
        ],
        "luminotes.download_products": [
          {
            "name": "local desktop extravaganza",
            "designed_for": "individuals",
            "storage_quota_bytes": None,
            "included_users": 1,
            "notebook_sharing": False,
            "notebook_collaboration": False,
            "user_admin": False,
            "fee": "30.00",
            "item_number": "5000",
            "filename": "test.exe",
            "button": u"",
          },
        ],
      },
      u"/files/download": {
        u"stream_response": True,
        u"encoding_filter.on": False,
      },
      u"/files/progress": {
        u"stream_response": True,
      },
    }

    cherrypy.root = Root( self.database, self.settings, suppress_exceptions = True )
    cherrypy.config.update( self.settings )
    cherrypy.server.start( init_only = True, server_class = None )

    # since we only want to test the controller, use the stub view for all exposed methods
    import controller.Expose
    Stub_view.result = None
    controller.Expose.view_override = Stub_view

  def tearDown( self ):
    self.database.close()
    cherrypy.server.stop()

  def http_get( self, http_path, headers = None, session_id = None, pretend_https = False ):
    """
    Perform an HTTP GET with the given path on the test server. Return the result dict as returned
    by the invoked method.
    """
    if headers is None:
      headers = []

    if session_id:
      headers.append( ( u"Cookie", "session_id=%s" % session_id ) ) # will break if unicode is used for the value

    if pretend_https:
      proxy_ip = self.settings[ "global" ].get( u"luminotes.https_proxy_ip" )
    else:
      proxy_ip = self.settings[ "global" ].get( u"luminotes.http_proxy_ip" )

    request = cherrypy.server.request( ( proxy_ip, 1234 ), u"127.0.0.5" )
    response = request.run( "GET %s HTTP/1.0" % str( http_path ), headers = headers, rfile = StringIO() )
    session_id = response.simple_cookie.get( u"session_id" )
    if session_id: session_id = session_id.value

    try:
      if Stub_view.result is not None:
        result = Stub_view.result
        Stub_view.result = None
      else:
        result = dict(
          status = response.status,
          headers = response.headers,
          body = response.body,
        )

      result[ u"session_id" ] = session_id
      return result
    finally:
      request.close()

  def http_post( self, http_path, form_args, headers = None, session_id = None ):
    """
    Perform an HTTP POST with the given path on the test server, sending the provided form_args
    dict. Return the result dict as returned by the invoked method.
    """
    from urllib import urlencode
    post_data = urlencode( form_args )

    if headers is None:
      headers = []

    headers.extend( [
      ( u"Content-Type", u"application/x-www-form-urlencoded" ),
      ( u"Content-Length", unicode( len( post_data ) ) ),
    ] )

    if session_id:
      headers.append( ( u"Cookie", "session_id=%s" % session_id ) ) # will break if unicode is used for the value

    request = cherrypy.server.request( ( u"127.0.0.1", 1234 ), u"127.0.0.5" )
    response = request.run( "POST %s HTTP/1.0" % str( http_path ), headers = headers, rfile = StringIO( post_data ) )
    session_id = response.simple_cookie.get( u"session_id" )
    if session_id: session_id = session_id.value

    try:
      if Stub_view.result is not None:
        result = Stub_view.result
        Stub_view.result = None
      else:
        result = dict(
          status = response.status,
          headers = response.headers,
          body = response.body,
        )

      result[ u"session_id" ] = session_id
      return result
    finally:
      request.close()

  def http_upload( self, http_path, form_args, filename, file_data, content_type, simulate_cancel = False, headers = None, session_id = None ):
    """
    Perform an HTTP POST with the given path on the test server, sending the provided form_args
    and file_data as a multipart form file upload. Return the result dict as returned by the
    invoked method.
    """
    boundary = "boundarygoeshere"
    post_data = [ "--%s\n" % boundary ]

    for ( name, value ) in form_args.items():
      post_data.append( 'Content-Disposition: form-data; name="%s"\n\n%s\n--%s\n' % (
        str( name ), str( value ), boundary
      ) )

    post_data.append( 'Content-Disposition: form-data; name="upload"; filename="%s"\n' % (
      filename.encode( "utf8" )
    ) )
    post_data.append( "Content-Type: %s\nContent-Transfer-Encoding: binary\n\n%s\n--%s--\n" % (
      content_type, file_data, boundary
    ) )

    if headers is None:
      headers = []

    post_data = "".join( post_data )
    headers.append( ( "Content-Type", "multipart/form-data; boundary=%s" % boundary ) )

    if "Content-Length" not in [ name for ( name, value ) in headers ]:
      headers.append( ( "Content-Length", str( len( post_data ) ) ) )

    if session_id:
      headers.append( ( u"Cookie", "session_id=%s" % session_id ) ) # will break if unicode is used for the value

    if simulate_cancel:
      file_wrapper = Truncated_StringIO( post_data )
    else:
      file_wrapper = Wrapped_StringIO( post_data )

    request = cherrypy.server.request( ( u"127.0.0.1", 1234 ), u"127.0.0.5" )
    response = request.run( "POST %s HTTP/1.0" % str( http_path ), headers = headers, rfile = file_wrapper )
    session_id = response.simple_cookie.get( u"session_id" )
    if session_id: session_id = session_id.value

    try:
      if Stub_view.result is not None:
        result = Stub_view.result
        Stub_view.result = None
      else:
        result = dict(
          status = response.status,
          headers = response.headers,
          body = response.body,
        )

      result[ u"session_id" ] = session_id
      return result
    finally:
      request.close()
