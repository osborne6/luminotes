import cherrypy
from controller.Scheduler import Scheduler
from controller.Database import Database
from controller.test.Stub_view import Stub_view
from config import Common
from datetime import datetime
from StringIO import StringIO


class Test_controller( object ):
  def setUp( self ):
    from controller.Root import Root
    cherrypy.lowercase_api = True
    self.scheduler = Scheduler()
    self.database = Database( self.scheduler, database_path = None )
    self.settings = {
      u"global": {
        u"luminotes.http_url" : u"http://luminotes.com",
        u"luminotes.https_url" : u"https://luminotes.com",
        u"luminotes.http_proxy_ip" : u"127.0.0.1",
        u"luminotes.https_proxy_ip" : u"127.0.0.2",
        u"luminotes.support_email": "unittest@luminotes.com",
        u"luminotes.rate_plans": [
          {
            u"name": u"super",
            u"storage_quota_bytes": 1337,
          },
          {
            u"name": "extra super",
            u"storage_quota_bytes": 31337,
          },
        ],
      },
    }

    cherrypy.root = Root( self.scheduler, self.database, self.settings )
    cherrypy.config.update( Common.settings )
    cherrypy.config.update( { u"server.log_to_screen": False } )
    cherrypy.server.start( init_only = True, server_class = None )

    # since we only want to test the controller, use the stub view for all exposed methods
    import controller.Expose
    Stub_view.result = None
    controller.Expose.view_override = Stub_view

  def tearDown( self ):
    cherrypy.server.stop()
    self.scheduler.shutdown()

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
    response = request.run( "GET %s HTTP/1.0" % http_path, headers = headers, rfile = StringIO() )
    session_id = response.simple_cookie.get( u"session_id" )
    if session_id: session_id = session_id.value

    try:
      if Stub_view.result is not None:
        result = Stub_view.result
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
    response = request.run( "POST %s HTTP/1.0" % http_path, headers = headers, rfile = StringIO( post_data ) )
    session_id = response.simple_cookie.get( u"session_id" )
    if session_id: session_id = session_id.value

    try:
      if Stub_view.result is not None:
        result = Stub_view.result
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
