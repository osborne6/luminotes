#!/usr/bin/python2.4

import os
import os.path
from controller.Database import Database
from controller.Scheduler import Scheduler


class Dumper( object ):
  def __init__( self, scheduler, database ):
    self.scheduler = scheduler
    self.database = database

    thread = self.dump_database()
    self.scheduler.add( thread )
    self.scheduler.wait_for( thread )

  def dump_database( self ):
    for key in self.database._Database__db.keys():
      self.database.load( key, self.scheduler.thread )
      value = ( yield Scheduler.SLEEP )
      print "%s: %s" % ( key, value )

    yield None


def main():
  scheduler = Scheduler()
  database = Database( scheduler, "data.db" )
  initializer = Dumper( scheduler, database )
  scheduler.wait_until_idle()


if __name__ == "__main__":
  main()
