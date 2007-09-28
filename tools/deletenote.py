#!/usr/bin/python2.5

import os
import os.path
from config.Common import settings
from controller.Database import Database
from controller.Scheduler import Scheduler
from model.Note import Note
from tools.initdb import fix_note_contents


class Deleter( object ):
  HTML_PATH = u"static/html"

  def __init__( self, scheduler, database ):
    self.scheduler = scheduler
    self.database = database

    threads = (
      self.delete_note(),
    )

    for thread in threads:
      self.scheduler.add( thread )
      self.scheduler.wait_for( thread )

  def delete_note( self ):
    self.database.load( u"User anonymous", self.scheduler.thread )
    anonymous = ( yield Scheduler.SLEEP )
    read_only_main_notebook = anonymous.notebooks[ 0 ]
    main_notebook = anonymous.notebooks[ 0 ]._Read_only_notebook__wrapped
    startup_notes = []

    for note in main_notebook.notes:
      if note and note.title == "try it out": # FIXME: make the note title to delete not hard-coded
        print "deleting note %s: %s" % ( note.object_id, note.title )
        main_notebook.remove_note( note )

    self.database.save( main_notebook )


def main( args ):
  print "IMPORTANT: Stop the Luminotes server before running this program."

  scheduler = Scheduler()
  database = Database( scheduler, "data.db" )
  initializer = Deleter( scheduler, database )
  scheduler.wait_until_idle()


if __name__ == "__main__":
  import sys
  main( sys.argv[ 1: ] )
