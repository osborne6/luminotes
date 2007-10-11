import cherrypy
from controller.Database import Database
from controller.Root import Root
from config import Common


def main( args ):
  database = Database()

  cherrypy.config.update( Common.settings )

  if len( args ) > 0 and args[ 0 ] == "-d":
    from config import Development
    settings = Development.settings
  else:
    from config import Production
    settings = Production.settings

  cherrypy.config.update( settings )

  cherrypy.lowercase_api = True
  root = Root( database, cherrypy.config.configMap )
  cherrypy.root = root

  cherrypy.server.start()


if __name__ == "__main__":
  import sys
  main( sys.argv[ 1: ] )
