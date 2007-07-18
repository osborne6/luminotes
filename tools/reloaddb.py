#!/usr/bin/python2.4

import os
import os.path
from controller.Database import Database
from controller.Scheduler import Scheduler


class Reloader( object ):
  def __init__( self, scheduler, database ):
    self.scheduler = scheduler
    self.database = database

    thread = self.reload_database()
    self.scheduler.add( thread )
    self.scheduler.wait_for( thread )

  def reload_database( self ):
    for key in self.database._Database__db.keys():
      self.database.reload( key, self.scheduler.thread )
      yield Scheduler.SLEEP 

    yield None


def main():
  scheduler = Scheduler()
  database = Database( scheduler, "data.db" )
  initializer = Reloader( scheduler, database )
  scheduler.wait_until_idle()


if __name__ == "__main__":
  main()
