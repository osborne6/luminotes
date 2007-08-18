#!/usr/bin/python2.5

import os
import os.path
import sys
from config.Common import settings
from controller.Database import Database
from controller.Scheduler import Scheduler


class Resetter( object ):
  def __init__( self, scheduler, database, username ):
    self.scheduler = scheduler
    self.database = database
    self.username = username
    self.password = None

    self.prompt_for_password()

    threads = (
      self.reset_password(),
    )

    for thread in threads:
      self.scheduler.add( thread )
      self.scheduler.wait_for( thread )

  def prompt_for_password( self ):
    print "enter new password for user %s: " % self.username,
    sys.stdout.flush()
    self.password = sys.stdin.readline().strip()
    print

  def reset_password( self ):
    self.database.load( u"User %s" % self.username, self.scheduler.thread )
    user = ( yield Scheduler.SLEEP )
    if user is None:
      raise Exception( "user %s is unknown" % self.username )
      

    user.password = self.password
    self.database.save( user )
    print "password reset"


def main( program_name, args ):
  print "IMPORTANT: Stop the Luminotes server before running this program."

  if len( args ) == 0:
    print "usage: %s username" % program_name
    sys.exit( 1 )

  scheduler = Scheduler()
  database = Database( scheduler, "data.db" )
  initializer = Resetter( scheduler, database, args[ 0 ] )
  scheduler.wait_until_idle()


if __name__ == "__main__":
  import sys
  main( sys.argv[ 0 ], sys.argv[ 1: ] )
