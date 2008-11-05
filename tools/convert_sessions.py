# Basic script to convert file-based CherryPy sessions to PostgreSQL-backed sessions.

import os
import cPickle as pickle
from controller.Database import Database
from controller.Session_storage import Session_storage


def main( args ):
  import cherrypy
  from config import Common

  cherrypy.config.update( Common.settings )

  if args and "-d" in args:
    from config import Development
    settings = Development.settings
  else:
    from config import Production
    settings = Production.settings

  cherrypy.config.update( settings )

  database = Database(
    host = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_host" ),
    ssl_mode = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_ssl_mode" ),
    data_dir = ".",
  )

  class Stub_root( object ):
    def __init__( self, database ):
      self.database = database

  cherrypy.root = Stub_root( database )
  sessions = Session_storage()
  session_count = 0

  for session_filename in os.listdir( u"session/" ):
    pickled_data = file( u"session/%s" % session_filename ).read()
    ( data, expiration_time ) = pickle.loads( pickled_data )
    session_id = data[ u"_id" ]

    sessions.save( session_id, data, expiration_time )
    session_count += 1

  print "converted %d sessions" % session_count 


if __name__ == "__main__":
  import sys
  main( sys.argv[ 1: ] )
