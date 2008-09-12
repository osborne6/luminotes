#!/usr/bin/python2.4

import os
import os.path
import sys
import cherrypy
from controller.Database import Database
from model.Download_access import Download_access


class Link_maker( object ):
  """
  Create a product download access record and print the download link for it.
  """
  def __init__( self, database, settings, item_number, transaction_id = None ):
    self.database = database
    self.settings = settings
    self.item_number = item_number
    self.transaction_id = transaction_id

    self.grant_access()
    self.database.commit()

  def grant_access( self ):
    access_id = self.database.next_id( Download_access, commit = False )
    download_access = Download_access.create( access_id, self.item_number, self.transaction_id )
    self.database.save( download_access, commit = False )

    https_url = self.settings[ u"global" ][ u"luminotes.https_url" ]
    print u"%s/d/%s" % ( https_url, access_id )


def main( args ):
  import cherrypy
  from config import Common

  cherrypy.config.update( Common.settings )
  desktop = False

  if args and "-d" in args:
    from config import Development
    settings = Development.settings
    args.remove( "-d" )
  elif args and "-l" in args:
    from config import Desktop
    settings = Desktop.settings
    desktop = True
    args.remove( "-l" )
  else:
    from config import Production
    settings = Production.settings

  cherrypy.config.update( settings )

  database = Database(
    host = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_host" ),
    ssl_mode = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_ssl_mode" ),
    data_dir = ".",
  )
  ranker = Link_maker( database, cherrypy.config.configMap, *args )


if __name__ == "__main__":
  main( sys.argv[ 1: ] )
