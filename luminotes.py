#!/usr/bin/python2.4

import socket
import cherrypy
from controller.Database import Database
from controller.Root import Root
from config import Common


SOCKET_TIMEOUT_SECONDS = 60


def main( args ):
  socket.setdefaulttimeout( SOCKET_TIMEOUT_SECONDS )

  cherrypy.config.update( Common.settings )

  if len( args ) > 0 and args[ 0 ] == "-d":
    from config import Development
    settings = Development.settings
  else:
    from config import Production
    settings = Production.settings

  cherrypy.config.update( settings )

  database = Database(
    host = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_host" ),
    ssl_mode = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_ssl_mode" ),
  )

  cherrypy.lowercase_api = True
  root = Root( database, cherrypy.config.configMap )
  cherrypy.root = root

  cherrypy.server.start()


if __name__ == "__main__":
  import sys
  main( sys.argv[ 1: ] )
