#!/usr/bin/python2.5

import os
import os.path
import sys
from config.Common import settings
from controller.Database import Database
from controller.Scheduler import Scheduler


class Setter( object ):
  def __init__( self, scheduler, database, username, email_address ):
    self.scheduler = scheduler
    self.database = database
    self.username = username
    self.email_address = email_address
    self.password = None

    threads = (
      self.set_email_address(),
    )

    for thread in threads:
      self.scheduler.add( thread )
      self.scheduler.wait_for( thread )

  def set_email_address( self ):
    self.database.load( u"User %s" % self.username, self.scheduler.thread )
    user = ( yield Scheduler.SLEEP )
    if user is None:
      raise Exception( "user %s is unknown" % self.username )

    user.email_address = self.email_address
    self.database.save( user )
    print "email set"


def main( program_name, args ):
  print "IMPORTANT: Stop the Luminotes server before running this program."

  if len( args ) < 2:
    print "usage: %s username emailaddress" % program_name
    sys.exit( 1 )

  scheduler = Scheduler()
  database = Database( scheduler, "data.db" )
  initializer = Setter( scheduler, database, *args )
  scheduler.wait_until_idle()


if __name__ == "__main__":
  import sys
  main( sys.argv[ 0 ], sys.argv[ 1: ] )
