#!/usr/bin/python2.5

import os
import os.path
from controller.Database import Database
from controller.Scheduler import Scheduler
from model.Notebook import Notebook
from model.Read_only_notebook import Read_only_notebook
from model.Note import Note
from model.User import User


class Initializer( object ):
  HTML_PATH = u"static/html"
  NOTE_FILES = [ # the second element of the tuple is whether to show the note on startup
    ( u"navigation.html", True ),
    ( u"about.html", True ),
    ( u"features.html", True ),
    ( u"take a tour.html", False ),
    ( u"try it out.html", False ),
    ( u"faq.html", False ),
    ( u"contact us.html", False ),
    ( u"login.html", False ),
    ( u"password reset.html", False ),
    ( u"supported browsers.html", False ),
    ( u"advanced browser features.html", False ),
  ]

  def __init__( self, scheduler, database ):
    self.scheduler = scheduler
    self.database = database
    self.main_notebook = None
    self.read_only_main_notebook = None
    self.anonymous = None

    threads = (
      self.create_main_notebook(),
      self.create_anonymous_user(),
    )

    for thread in threads:
      self.scheduler.add( thread )
      self.scheduler.wait_for( thread )

  def create_main_notebook( self ):
    # create the main notebook and all of its notes
    self.database.next_id( self.scheduler.thread )
    main_notebook_id = ( yield Scheduler.SLEEP )
    self.main_notebook = Notebook( main_notebook_id, u"Luminotes" )

    # create the read-only view of the main notebook
    self.database.next_id( self.scheduler.thread )
    read_only_main_notebook_id = ( yield Scheduler.SLEEP )
    self.read_only_main_notebook = Read_only_notebook( read_only_main_notebook_id, self.main_notebook )

    # create an id for each note
    note_ids = {}
    for ( filename, startup ) in self.NOTE_FILES:
      self.database.next_id( self.scheduler.thread )
      note_ids[ filename ] = ( yield Scheduler.SLEEP )

    for ( filename, startup ) in self.NOTE_FILES:
      full_filename = os.path.join( self.HTML_PATH, filename )
      contents = fix_note_contents( file( full_filename ).read(), read_only_main_notebook_id, note_ids )

      note = Note( note_ids[ filename ], contents )
      self.main_notebook.add_note( note )

      if startup:
        self.main_notebook.add_startup_note( note )

    self.database.save( self.main_notebook )
    self.database.save( self.read_only_main_notebook )

  def create_anonymous_user( self ):
    # create the anonymous user
    self.database.next_id( self.scheduler.thread )
    anonymous_user_id = ( yield Scheduler.SLEEP )
    notebooks = [ self.read_only_main_notebook ]
    self.anonymous = User( anonymous_user_id, u"anonymous", None, None, notebooks )
    self.database.save( self.anonymous )


def main():
  print "IMPORTANT: Stop the Luminotes server before running this program."

  if os.path.exists( "data.db" ):
    os.remove( "data.db" )

  scheduler = Scheduler()
  database = Database( scheduler, "data.db" )
  initializer = Initializer( scheduler, database )
  scheduler.wait_until_idle()


def fix_note_contents( contents, notebook_id, note_ids ):
  import re
  from config.Common import settings

  LINK_PATTERN = re.compile( '(<a href=")([^"]+?note_id=)([^"]*)("[^>]*>)([^<]*)(</a>)' )

  # plug in the notebook id where appropriate
  contents = contents.replace( "%s", notebook_id )

  # stitch together note links to use the actual note ids of the referenced notes.
  # also, use the https URL for certain links if one is configured
  def fix_link( match ):
    title = match.group( 5 )
    https_url = u""

    if title in ( u"try it out", u"login" ):
      https_url = settings[ u"global" ].get( u"luminotes.https_url", u"" )

    return u"".join( [
      match.group( 1 ), https_url, match.group( 2 ), note_ids.get( title + u".html", u"new" ),
      match.group( 4 ), match.group( 5 ), match.group( 6 ),
    ] )

  return LINK_PATTERN.sub( fix_link, contents )


if __name__ == "__main__":
  main()
