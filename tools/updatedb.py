#!/usr/bin/python2.4

import os
import os.path
from config.Common import settings
from controller.Database import Database
from controller.Scheduler import Scheduler
from model.Note import Note
from tools.initdb import fix_note_contents


class Initializer( object ):
  HTML_PATH = u"static/html"
  NOTE_FILES = [ # the second element of the tuple is whether to show the note on startup
    ( u"about.html", True ),
    ( u"features.html", True ),
    ( u"take a tour.html", False ),
    ( u"try it out.html", False ),
    ( u"login.html", False ),
    ( u"password reset.html", False ),
    ( u"supported browsers.html", False ),
    ( u"advanced browser features.html", False ),
  ]

  def __init__( self, scheduler, database, navigation_note_id = None ):
    self.scheduler = scheduler
    self.database = database
    self.navigation_note_id = navigation_note_id

    threads = (
      self.update_main_notebook(),
    )

    for thread in threads:
      self.scheduler.add( thread )
      self.scheduler.wait_for( thread )

  def update_main_notebook( self ):
    self.database.load( u"User anonymous", self.scheduler.thread )
    anonymous = ( yield Scheduler.SLEEP )
    read_only_main_notebook = anonymous.notebooks[ 0 ]
    main_notebook = anonymous.notebooks[ 0 ]._Read_only_notebook__wrapped
    startup_notes = []

    # get the id for each note
    note_ids = {}
    for ( filename, startup ) in self.NOTE_FILES:
      title = filename.replace( u".html", u"" )
      note = main_notebook.lookup_note_by_title( title )
      note_ids[ filename ] = note.object_id

    # update the navigation note if its id was given
    if self.navigation_note_id:
      self.database.next_id( self.scheduler.thread )
      next_id = ( yield Scheduler.SLEEP )
      note = main_notebook.lookup_note( self.navigation_note_id )
      self.update_note( "navigation.html", True, main_notebook, read_only_main_notebook, startup_notes, next_id, note_ids, note )

    # update all of the notes in the main notebook
    for ( filename, startup ) in self.NOTE_FILES:
      self.database.next_id( self.scheduler.thread )
      next_id = ( yield Scheduler.SLEEP )
      title = filename.replace( u".html", u"" )
      note = main_notebook.lookup_note_by_title( title )
      self.update_note( filename, startup, main_notebook, read_only_main_notebook, startup_notes, next_id, note_ids, note )

    for note in startup_notes:
      main_notebook.add_startup_note( note )

    main_notebook.name = u"Luminotes"
    self.database.save( main_notebook )

  def update_note( self, filename, startup, main_notebook, read_only_main_notebook, startup_notes, next_id, note_ids, note = None ):
    full_filename = os.path.join( self.HTML_PATH, filename )
    contents = fix_note_contents( file( full_filename ).read(), read_only_main_notebook.object_id, note_ids )

    if note:
      main_notebook.update_note( note, contents )
    # if for some reason the note isn't present, create it
    else:
      note = Note( next_id, contents )
      main_notebook.add_note( note )

    main_notebook.remove_startup_note( note )
    if startup:
      startup_notes.append( note )


def main( args ):
  scheduler = Scheduler()
  database = Database( scheduler, "data.db" )
  initializer = Initializer( scheduler, database, args and args[ 0 ] or None )
  scheduler.wait_until_idle()


if __name__ == "__main__":
  import sys
  main( sys.argv[ 1: ] )
