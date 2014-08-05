#!/usr/bin/python

import os
import sys
import stat
import socket
import os.path
import urllib2 as urllib
import optparse
import cherrypy
import webbrowser
from controller.Database import Database
from controller.Schema_upgrader import Schema_upgrader
from controller.Root import Root
from config import Common
from config.Version import VERSION


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


def main( options ):
  change_to_main_dir()

  cherrypy.config.update( Common.settings )
  if options.development:
    from config import Development
    settings = Development.settings
  elif options.desktop:
    from config import Desktop
    settings = Desktop.settings
  else:
    from config import Production
    settings = Production.settings

  cherrypy.config.update( settings )

  # Don't launch web browser if -w flag is set
  if options.no_webbrowser:
    launch_browser = False
  else:
    launch_browser = cherrypy.config[ u"luminotes.launch_browser"]

  socket.setdefaulttimeout( INITIAL_SOCKET_TIMEOUT_SECONDS )
  port_filename = cherrypy.config[ u"luminotes.port_file" ]
  socket_port = cherrypy.config[ u"server.socket_port" ]
  existing_socket_port = port_filename and os.path.exists( port_filename ) and file( port_filename ).read() or socket_port
  server_url = u"http://localhost:%s/" % existing_socket_port
  server_present = True

  # if requested, attempt to shutdown an existing server and exit
  if options.kill:
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

  server_url = u"http://127.0.0.1:%s/" % socket_port

  # remove the existing log files, if any
  try:
    log_access_file = cherrypy.config[ u"server.log_access_file" ]
    if log_access_file:
      os.remove( log_access_file )
  except OSError:
    pass

  try:
    log_file = cherrypy.config[ u"server.log_file" ]
    if log_file:
      os.remove( log_file )
  except OSError:
    pass

  socket.setdefaulttimeout( SOCKET_TIMEOUT_SECONDS )

  database = Database(
    host = cherrypy.config[ u"luminotes.db_host" ],
    ssl_mode = cherrypy.config[ u"luminotes.db_ssl_mode" ],
  )

  # if necessary, upgrade the database schema to match this current version of the code
  schema_upgrader = Schema_upgrader( database )
  schema_upgrader.upgrade_schema( to_version = VERSION )

  cherrypy.lowercase_api = True
  root = Root( database, cherrypy.config )
  cherrypy.tree.mount(root, '/', config=settings )

  cherrypy.engine.start_with_callback( callback, ( log_access_file, log_file, server_url, port_filename, socket_port, launch_browser ) )
  cherrypy.engine.block()


def callback( log_access_file, log_file, server_url, port_filename, socket_port, launch_browser = False ):
  # record our listening socket port
  if port_filename:
    port_file = file( port_filename, "w" )
    os.chmod( port_filename, stat.S_IRUSR | stat.S_IWUSR )
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

  # sys.frozen is from py2exe
  desktop_default = hasattr( sys, "frozen" )

  parser = optparse.OptionParser(
    usage = "usage: %prog [OPTIONS]\n" +
            "   OR: %prog --help",
    version = VERSION,
  )

  parser.add_option(
    "-l", "--desktop", 
    dest = "desktop",
    action = "store_true",
    default = desktop_default,
    help = "Run in Desktop mode %s" %
           ( "(DEFAULT)" if desktop_default else "" ),
  )

  parser.add_option(
    "-s", "--server", 
    dest = "desktop",
    action = "store_false",
    help = "Run in Server mode %s" %
           ( "(DEFAULT)" if not desktop_default else "" ),
  )

  parser.add_option(
    "-d", "--developement", 
    dest = "development",
    action = "store_true",
    help = "Run in Development mode",
  )

  parser.add_option(
    "-k", "--kill",
    dest = "kill",
    action = "store_true",
    help = "Attempt to shutdown existing server and exit",
  )

  parser.add_option(
    "-w", "--no_webbrowser",
    dest = "no_webbrowser",
    action = "store_true",
    help = "Don't autolaunch web browser in Desktop mode",
  )

  ( options, args ) = parser.parse_args()
  if args != []:
    parser.error( "Unrecognised options: %s" % " ".join( args ) )

  main(options)
