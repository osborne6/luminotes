#!/usr/bin/python2.4

import os
import os.path
from controller.Database import Database
from controller.Scheduler import Scheduler
from model.Notebook import Notebook
from model.Read_only_notebook import Read_only_notebook
from model.Entry import Entry
from model.User import User


class Initializer( object ):
  HTML_PATH = u"static/html"
  ENTRY_FILES = [ # the second element of the tuple is whether to show the entry on startup
    ( u"navigation.html", True ),
    ( u"about.html", True ),
    ( u"features.html", True ),
    ( u"take a tour.html", False ),
    ( u"try it out.html", False ),
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
    self.user_notebook = None
    self.user = None
    self.anonymous = None

    threads = (
      self.create_main_notebook(),
      self.create_anonymous_user(),
      self.create_user_notebook(),
      self.create_user(),
    )

    for thread in threads:
      self.scheduler.add( thread )
      self.scheduler.wait_for( thread )

  def create_main_notebook( self ):
    # create the main notebook and all of its entries
    self.database.next_id( self.scheduler.thread )
    main_notebook_id = ( yield Scheduler.SLEEP )
    self.main_notebook = Notebook( main_notebook_id, u"Limited Medium" )

    for ( filename, startup ) in self.ENTRY_FILES:
      full_filename = os.path.join( self.HTML_PATH, filename )
      contents = file( full_filename ).read()

      self.database.next_id( self.scheduler.thread )
      entry_id = ( yield Scheduler.SLEEP )

      entry = Entry( entry_id, contents )
      self.main_notebook.add_entry( entry )

      if startup:
        self.main_notebook.add_startup_entry( entry )

    self.database.save( self.main_notebook )

    # create the read-only view of the main notebook
    self.database.next_id( self.scheduler.thread )
    read_only_main_notebook_id = ( yield Scheduler.SLEEP )
    self.read_only_main_notebook = Read_only_notebook( read_only_main_notebook_id, self.main_notebook )
    self.database.save( self.read_only_main_notebook )

  def create_anonymous_user( self ):
    # create the anonymous user
    self.database.next_id( self.scheduler.thread )
    anonymous_user_id = ( yield Scheduler.SLEEP )
    notebooks = [ self.read_only_main_notebook ]
    self.anonymous = User( anonymous_user_id, u"anonymous", None, None, notebooks )
    self.database.save( self.anonymous )

  def create_user_notebook( self ):
    # create the user notebook along with a startup entry
    self.database.next_id( self.scheduler.thread )
    user_notebook_id = ( yield Scheduler.SLEEP )
    self.user_notebook = Notebook( user_notebook_id, u"my notebook" )

    self.database.next_id( self.scheduler.thread )
    entry_id = ( yield Scheduler.SLEEP )
    entry = Entry( entry_id, u"<h3>" )
    self.user_notebook.add_entry( entry )
    self.user_notebook.add_startup_entry( entry )

    self.database.save( self.user_notebook )

  def create_user( self ):
    # create the user
    self.database.next_id( self.scheduler.thread )
    user_id = ( yield Scheduler.SLEEP )
    notebooks = [ self.user_notebook ]
    self.user = User( user_id, u"witten", u"dev", u"witten@torsion.org", notebooks )

    self.database.save( self.user )


def main():
  if os.path.exists( "data.db" ):
    os.remove( "data.db" )

  scheduler = Scheduler()
  database = Database( scheduler, "data.db" )
  initializer = Initializer( scheduler, database )
  scheduler.wait_until_idle()


if __name__ == "__main__":
  main()
