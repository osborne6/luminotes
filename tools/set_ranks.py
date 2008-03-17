#!/usr/bin/python2.4

import os
import os.path
from controller.Database import Database
from model.Notebook import Notebook
from model.User import User


class Ranker( object ):
  def __init__( self, database ):
    self.database = database

    self.rank_notebooks()
    self.database.commit()

  def rank_notebooks( self ):
    users = self.database.select_many( User, u"select * from luminotes_user_current where username is not null and username != 'anonymous';" )

    # rank the notebooks for each user
    for user in users:
      rank = 0
      notebooks = self.database.select_many( Notebook, user.sql_load_notebooks( parents_only = True, undeleted_only = True ) )

      for notebook in notebooks:
        self.database.execute( user.sql_update_notebook_rank( notebook.object_id, rank ), commit = False )
        rank += 1


def main( args ):
  database = Database()
  ranker = Ranker( database )


if __name__ == "__main__":
  import sys
  main( sys.argv[ 1: ] )
