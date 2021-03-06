#!/usr/bin/python2.4

import os
import os.path
import sys
from controller.Database import Database
from controller.Users import Users
from model.Notebook import Notebook
from model.User import User


class Plan_setter( object ):
  """
  Set the rate plan for a particular user.
  """
  def __init__( self, database, settings, user_id, rate_plan ):
    self.database = database
    self.user_id = user_id
    self.rate_plan = int( rate_plan )

    rate_plans = settings[ u"global" ][ u"luminotes.rate_plans" ]
    self.users = Users( database, None, None, None, None, rate_plans, [] )

    self.set_plan()
    self.database.commit()

  def set_plan( self ):
    user = self.database.load( User, self.user_id )

    if not user:
      print "user id %s unknown" % self.user_id
      sys.exit( 1 )

    user.rate_plan = self.rate_plan
    self.database.save( user, commit = False )

    # update a user's group membership as a result of a rate plan change
    self.users.update_groups( user )

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
  ranker = Plan_setter( database, cherrypy.config.configMap, *args )


if __name__ == "__main__":
  main( sys.argv[ 1: ] )
