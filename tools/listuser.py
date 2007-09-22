#!/usr/bin/python2.5

import os
import os.path
import sys
from config.Common import settings
from controller.Database import Database
from controller.Scheduler import Scheduler


class Lister( object ):
  def __init__( self, scheduler, database, username ):
    self.scheduler = scheduler
    self.database = database
    self.username = username

    threads = (
      self.list_user(),
    )

    for thread in threads:
      self.scheduler.add( thread )
      self.scheduler.wait_for( thread )

  def list_user( self ):
    self.database.load( u"User %s" % self.username, self.scheduler.thread )
    user = ( yield Scheduler.SLEEP )
    if user is None:
      print "user %s is unknown" % self.username
    else:
      print "user %s: %s" % ( self.username, user )


def main( program_name, args ):
  if len( args ) == 0:
    print "usage: %s username" % program_name
    sys.exit( 1 )

  scheduler = Scheduler()
  database = Database( scheduler, "data.db" )
  initializer = Lister( scheduler, database, args[ 0 ] )
  scheduler.wait_until_idle()


if __name__ == "__main__":
  import sys
  main( sys.argv[ 0 ], sys.argv[ 1: ] )
