#!/usr/bin/python2.4

import sys
import socket
import os.path
import urllib2 as urllib
import cherrypy
import webbrowser
from controller.Database import Database
from controller.Root import Root
from config import Common


INITIAL_SOCKET_TIMEOUT_SECONDS = 1
SOCKET_TIMEOUT_SECONDS = 60


def change_to_main_dir():
  """
  Change to the directory where the executable / main script is located.
  """
  if hasattr( sys, "frozen" ):
    path = os.path.dirname( unicode( sys.executable, sys.getfilesystemencoding() ) )
  else:
    path = os.path.dirname( unicode( __file__, sys.getfilesystemencoding() ) )

  if path:
    os.chdir( path )


def main( args ):
  change_to_main_dir()

  if sys.platform.startswith( "win" ):
    sys.stderr = sys.stdout

  cherrypy.config.update( Common.settings )

  if args and "-d" in args:
    from config import Development
    settings = Development.settings
  # sys.frozen is from py2exe
  elif args and "-l" in args or hasattr( sys, "frozen" ):
    from config import Desktop
    settings = Desktop.settings
  else:
    from config import Production
    settings = Production.settings

  cherrypy.config.update( settings )

  launch_browser = cherrypy.config.configMap[ u"global" ].get( u"luminotes.launch_browser" )

  socket.setdefaulttimeout( INITIAL_SOCKET_TIMEOUT_SECONDS )
  server_url = u"http://localhost:%d/" % cherrypy.config.configMap[ u"global" ].get( u"server.socket_port" )
  server_present = True

  # if requested, attempt to shutdown an existing server and exit
  if args and "-k" in args:
    try:
      urllib.urlopen( "%sshutdown" % server_url )
    except urllib.URLError:
      pass
    sys.exit( 0 )

  # check to see if the server is already running
  try:
    urllib.urlopen( "%sping" % server_url )
  except urllib.URLError:
    server_present = False

  if server_present is True:
    print "Luminotes server is already running. aborting"

    if launch_browser is True:
      webbrowser.open_new( server_url )

    sys.exit( 1 )

  socket.setdefaulttimeout( SOCKET_TIMEOUT_SECONDS )

  database = Database(
    host = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_host" ),
    ssl_mode = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_ssl_mode" ),
  )

  cherrypy.lowercase_api = True
  root = Root( database, cherrypy.config.configMap )
  cherrypy.root = root

  if launch_browser is True:
    cherrypy.server.start_with_callback( webbrowser.open_new, ( server_url, ) )
  else:
    cherrypy.server.start()


if __name__ == "__main__":
  main( sys.argv[ 1: ] )
