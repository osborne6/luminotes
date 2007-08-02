import cherrypy
from controller.Database import Database
from controller.Root import Root
from controller.Scheduler import Scheduler
from config import Common


def main( args ):
  scheduler = Scheduler()
  database = Database( scheduler, "data.db" )

  cherrypy.config.update( Common.settings )

  if len( args ) > 0 and args[ 0 ] == "-d":
    from config import Development
    settings = Development.settings
  else:
    from config import Production
    settings = Production.settings

  cherrypy.config.update( settings )

  cherrypy.lowercase_api = True
  root = Root( scheduler, database, cherrypy.config.configMap )
  cherrypy.root = root

  if scheduler.shutdown not in cherrypy.server.on_stop_server_list:
    cherrypy.server.on_stop_server_list.append( scheduler.shutdown )

  cherrypy.server.start()


if __name__ == "__main__":
  import sys
  main( sys.argv[ 1: ] )
