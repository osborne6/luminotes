#!/usr/bin/python2.4

import os
import os.path
import sys
import cherrypy
from datetime import datetime
from controller.Database import Database
from model.Notebook import Notebook
from model.Note import Note
from model.User import User
from model.Tag import Tag


class Thread_maker( object ):
  """
  Create a thread for a new forum.
  """
  def __init__( self, database, forum_name ):
    self.database = database
    self.forum_name = forum_name

    self.make_thread()
    self.database.commit()

  def make_thread( self ):
    title = u"Welcome to the Luminotes %s forum!" % self.forum_name

    # create a notebook thread to go in the forum
    notebook_id = self.database.next_id( Notebook, commit = False )
    thread_notebook = Notebook.create(
      notebook_id,
      title,
    )
    self.database.save( thread_notebook, commit = False )

    anonymous = self.database.select_one( User, User.sql_load_by_username( u"anonymous" ) )

    # add a single welcome note to the new thread
    note_id = self.database.next_id( Note, commit = False )
    note = Note.create(
      note_id,
      u"""
      <h3>%s</h3> You can discuss any Luminotes %s topics here. This is a public discussion
      forum, so please keep that in mind when posting. And have fun.
      """ % ( title, self.forum_name ),
      notebook_id,
      startup = True,
      rank = 0,
      user_id = anonymous.object_id,
      creation = datetime.now(),
    )
    self.database.save( note, commit = False )

    # load the forum tag, or create one if it doesn't exist
    tag = self.database.select_one( Tag, Tag.sql_load_by_name( u"forum", user_id = anonymous.object_id ) )
    if not tag:
      tag_id = self.database.next_id( Tag, commit = False )
      tag = Tag.create(
        tag_id,
        notebook_id = None, # this tag is not in the namespace of a single notebook
        user_id = anonymous.object_id,
        name = u"forum",
        description = u"discussion forum threads"
      )
      self.database.save( tag, commit = False )

    # associate the forum tag with the previously created notebook thread, and set that
    # association's value to forum_name
    self.database.execute(
      anonymous.sql_save_notebook_tag( notebook_id, tag.object_id, value = self.forum_name ),
      commit = False,
    )

    # give the anonymous user access to the new notebook thread
    self.database.execute(
      anonymous.sql_save_notebook( notebook_id, read_write = True, owner = False, own_notes_only = True ),
      commit = False,
    )


def main( args ):
  import cherrypy
  from config import Common

  cherrypy.config.update( Common.settings )
  desktop = False

  if args and "-d" in args:
    from config import Development
    settings = Development.settings
    args.remove( "-d" )
  elif args and "-l" in args:
    from config import Desktop
    settings = Desktop.settings
    desktop = True
    args.remove( "-l" )
  else:
    from config import Production
    settings = Production.settings

  cherrypy.config.update( settings )

  database = Database(
    host = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_host" ),
    ssl_mode = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_ssl_mode" ),
    data_dir = ".",
  )
  ranker = Thread_maker( database, *args )


if __name__ == "__main__":
  main( sys.argv[ 1: ] )
