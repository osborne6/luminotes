#!/usr/bin/python2.5

import os
import os.path
import sys
from config.Common import settings
from controller.Database import Database
from controller.Scheduler import Scheduler


class Setter( object ):
  def __init__( self, scheduler, database, username, rate_plan ):
    self.scheduler = scheduler
    self.database = database
    self.username = username
    self.rate_plan = rate_plan
    self.password = None

    threads = (
      self.set_rate_plan(),
    )

    for thread in threads:
      self.scheduler.add( thread )
      self.scheduler.wait_for( thread )

  def set_rate_plan( self ):
    self.database.load( u"User %s" % self.username, self.scheduler.thread )
    user = ( yield Scheduler.SLEEP )
    if user is None:
      raise Exception( "user %s is unknown" % self.username )

    user.rate_plan = int( self.rate_plan )
    self.database.save( user )
    print "password reset"


def main( program_name, args ):
  print "IMPORTANT: Stop the Luminotes server before running this program."

  if len( args ) < 2:
    print "usage: %s username rateplan" % program_name
    sys.exit( 1 )

  scheduler = Scheduler()
  database = Database( scheduler, "data.db" )
  initializer = Setter( scheduler, database, *args )
  scheduler.wait_until_idle()


if __name__ == "__main__":
  import sys
  main( sys.argv[ 0 ], sys.argv[ 1: ] )
