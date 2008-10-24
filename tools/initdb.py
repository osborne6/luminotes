#!/usr/bin/python2.4

import os
import os.path
import sys
from controller.Database import Database
from model.Notebook import Notebook
from model.Note import Note
from model.User import User


class Initializer( object ):
  HTML_PATH = u"static/html"
  NOTE_FILES = [ # the second element of the tuple is whether to show the note on startup
    ( u"sign up.html", False ),
    ( u"faq.html", False ),
    ( u"meet the team.html", False ),
    ( u"contact info.html", False ),
    ( u"login.html", False ),
    ( u"source code.html", False ),
    ( u"password reset.html", False ),
    ( u"advanced browser features.html", False ),
    ( u"supported browsers.html", False ),
    ( u"support.html", False ),
    ( u"enable JavaScript.html", False ),
  ]

  def __init__( self, database, host, settings, desktop, nuke = False ):
    self.database = database
    self.settings = settings
    self.desktop = desktop
    self.main_notebook = None
    self.anonymous = None

    if nuke is True:
      self.database.execute( file( "model/drop.sql" ).read(), commit = False )

    if host:
      self.database.execute( file( "model/schema.sql" ).read(), commit = False )
    else:
      self.database.execute_script( file( "model/schema.sqlite" ).read(), commit = False )

    self.create_main_notebook()
    self.create_anonymous_user()
    if desktop is True:
      self.create_desktop_user()

    self.database.commit()

  def create_main_notebook( self ):
    # create the main notebook
    main_notebook_id = self.database.next_id( Notebook )
    self.main_notebook = Notebook.create( main_notebook_id, u"Luminotes", rank = 0 )
    self.database.save( self.main_notebook, commit = False )

    # no need to create default notes for the desktop version
    if self.desktop is True:
      return

    # create an id for each note
    note_ids = {}
    for ( filename, startup ) in self.NOTE_FILES:
      note_ids[ filename ] = self.database.next_id( Note )

    rank = 0
    for ( filename, startup ) in self.NOTE_FILES:
      full_filename = os.path.join( self.HTML_PATH, filename )
      contents = fix_note_contents( file( full_filename ).read(), main_notebook_id, note_ids, self.settings )

      if startup:
        rank += 1

      note = Note.create( note_ids[ filename ], contents, notebook_id = self.main_notebook.object_id, startup = startup, rank = startup and rank or None )
      self.database.save( note, commit = False )

  def create_anonymous_user( self ):
    # create the anonymous user
    anonymous_user_id = self.database.next_id( User )
    self.anonymous = User.create( anonymous_user_id, u"anonymous", None, None )
    self.database.save( self.anonymous, commit = False )

    # give the anonymous user read-only access to the main notebook
    self.database.execute( self.anonymous.sql_save_notebook( self.main_notebook.object_id, read_write = False, owner = False ), commit = False )

  def create_desktop_user( self ):
    from controller.Users import Users
    users = Users(
      self.database,
      self.settings[ u"global" ].get( u"luminotes.http_url", u"" ),
      self.settings[ u"global" ].get( u"luminotes.https_url", u"" ),
      self.settings[ u"global" ].get( u"luminotes.support_email", u"" ),
      self.settings[ u"global" ].get( u"luminotes.payment_email", u"" ),
      self.settings[ u"global" ].get( u"luminotes.rate_plans", [] ),
      self.settings[ u"global" ].get( u"luminotes.download_products", [] ),
    )

    users.create_user( u"desktopuser" )


def main( args = None ):
  nuke = False

  import cherrypy
  from config import Common

  cherrypy.config.update( Common.settings )
  desktop = False

  if args and "-d" in args:
    from config import Development
    settings = Development.settings
  elif args and "-l" in args:
    from config import Desktop
    settings = Desktop.settings
    desktop = True
  else:
    from config import Production
    settings = Production.settings

  cherrypy.config.update( settings )

  if args and ( "-n" in args or "--nuke" in args ):
    nuke = True
    print "This will nuke the contents of the database before initializing it with default data. Continue (y/n)? ",
    confirmation = sys.stdin.readline().strip()
    print

    if confirmation.lower()[ 0 ] != 'y':
      print "Exiting without touching the database."
      return

  print "Initializing the database with default data."
  host = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_host" )
  database = Database(
    host = host,
    ssl_mode = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_ssl_mode" ),
    data_dir = ".",
  )
  initializer = Initializer( database, host, cherrypy.config.configMap, desktop, nuke )


def fix_note_contents( contents, notebook_id, note_ids, settings ):
  import re

  LINK_PATTERN = re.compile( '(<a\s+href=")([^"]+note_id=)([^"]*)("[^>]*>)(.*?)(</a>)' )
  TITLE_PATTERN = re.compile( ' title="(.*?)"' )

  # plug in the notebook id and support email address where appropriate
  contents = contents.replace( "%s", notebook_id )
  contents = contents.replace( "support@luminotes.com", settings[ u"global" ].get( u"luminotes.support_email", u"" ) )

  # stitch together note links to use the actual note ids of the referenced notes.
  # also, use the https URL for certain links if one is configured
  def fix_link( match ):
    title = match.group( 5 )
    title_match = TITLE_PATTERN.search( title )
    if title_match:
      title = title_match.group( 1 )

    https_url = u""

    if title in ( u"sign up", u"login" ):
      https_url = settings[ u"global" ].get( u"luminotes.https_url", u"" )

    return u"".join( [
      match.group( 1 ), https_url, match.group( 2 ), note_ids.get( title + u".html", u"new" ),
      match.group( 4 ), match.group( 5 ), match.group( 6 ),
    ] )

  return LINK_PATTERN.sub( fix_link, contents )


if __name__ == "__main__":
  import sys
  main( sys.argv[ 1: ] )
