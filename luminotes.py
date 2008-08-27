#!/usr/bin/python

import os
import sys
import stat
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
  port_filename = cherrypy.config.configMap[ u"global" ].get( u"luminotes.port_file" )
  socket_port = cherrypy.config.configMap[ u"global" ].get( u"server.socket_port" )
  existing_socket_port = port_filename and os.path.exists( port_filename ) and file( port_filename ).read() or socket_port
  server_url = u"http://localhost:%s/" % existing_socket_port
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

    sys.exit( 0 )

  server_url = u"http://localhost:%s/" % socket_port

  # remove the existing log files, if any
  try:
    log_access_file = cherrypy.config.configMap[ u"global" ].get( u"server.log_access_file" )
    if log_access_file:
      os.remove( log_access_file )
  except OSError:
    pass

  try:
    log_file = cherrypy.config.configMap[ u"global" ].get( u"server.log_file" )
    if log_file:
      os.remove( log_file )
  except OSError:
    pass

  socket.setdefaulttimeout( SOCKET_TIMEOUT_SECONDS )

  database = Database(
    host = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_host" ),
    ssl_mode = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_ssl_mode" ),
  )

  cherrypy.lowercase_api = True
  root = Root( database, cherrypy.config.configMap )
  cherrypy.root = root

  cherrypy.server.start_with_callback( callback, ( log_access_file, log_file, server_url, port_filename, socket_port, launch_browser ) )


def callback( log_access_file, log_file, server_url, port_filename, socket_port, launch_browser = False ):
  # record our listening socket port
  if port_filename:
    port_file = file( port_filename, "w" )
    port_file.write( "%s" % socket_port )
    port_file.close()

  # this causes cherrypy to create the access log
  if log_access_file:
    try:
      urllib.urlopen( "%sping" % server_url )
    except urllib.URLError:
      pass

  # give the cherrypy log files appropriate permissions
  if log_access_file and os.path.exists( log_access_file ):
    os.chmod( log_access_file, stat.S_IRUSR | stat.S_IWUSR )
  if log_file and os.path.exists( log_file ):
    os.chmod( log_file, stat.S_IRUSR | stat.S_IWUSR )

  if launch_browser:
    webbrowser.open_new( server_url )


if __name__ == "__main__":
  main( sys.argv[ 1: ] )
