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


class Blog_converter( object ):
  """
  Convert the Luminotes blog to be a forum, with one notebook thread per blog post.
  """
  def __init__( self, database, settings, blog_username ):
    self.database = database
    self.settings = settings
    self.blog_username = blog_username
    self.blog_notebook = self.load_original_blog_notebook()

    self.convert_posts_to_forum_threads()
    self.delete_original_blog_notebook()
    self.database.commit()

  def load_original_blog_notebook( self ):
    anonymous = self.database.select_one( User, User.sql_load_by_username( u"anonymous" ) )

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

    result = users.current( anonymous.object_id ) 
    blog_notebooks = [ nb for nb in result[ "notebooks" ] if nb.name == u"Luminotes blog" ]

    return blog_notebooks[ 0 ]

  def convert_posts_to_forum_threads( self ):
    notes = self.database.select_many( Note, self.blog_notebook.sql_load_recent_notes( reverse = True, start = 0, count = 1000 ) )

    for note in notes:
      self.convert_post( note )

  def convert_post( self, note ):
    # create a notebook thread to go in the forum
    notebook_id = self.database.next_id( Notebook, commit = False )
    thread_notebook = Notebook.create(
      notebook_id,
      note.title,
    )
    self.database.save( thread_notebook, commit = False )

    anonymous = self.database.select_one( User, User.sql_load_by_username( u"anonymous" ) )

    # move the given note into the newly created notebook thread
    note.notebook_id = notebook_id
    note.startup = True
    note.rank = 0
    self.database.save( note, commit = False )

    # load the forum tag
    forum_tag = self.database.select_one( Tag, Tag.sql_load_by_name( u"forum", user_id = anonymous.object_id ) )

    # associate the forum tag with the previously created notebook thread, and set that
    # association's value to the forum name
    self.database.execute(
      anonymous.sql_save_notebook_tag( notebook_id, forum_tag.object_id, value = u"blog" ),
      commit = False,
    )

    # give the anonymous user access to the new notebook thread
    self.database.execute(
      anonymous.sql_save_notebook( notebook_id, read_write = True, owner = False, own_notes_only = True ),
      commit = False,
    )

    blog_user = self.database.select_one( User, User.sql_load_by_username( self.blog_username ) )

    self.database.execute(
      blog_user.sql_save_notebook( notebook_id, read_write = True, owner = True ),
      commit = False,
    )

  def delete_original_blog_notebook( self ):
    self.blog_notebook.deleted = True
    self.database.save( self.blog_notebook, commit = False )


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
  ranker = Blog_converter( database, cherrypy.config.configMap, *args )


if __name__ == "__main__":
  main( sys.argv[ 1: ] )
