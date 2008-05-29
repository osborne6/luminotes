#!/usr/bin/python2.4

import os
import os.path
import sys
from controller.Database import Database
from model.Notebook import Notebook
from model.User import User


class Plan_setter( object ):
  """
  Set the rate plan for a particular user.
  """
  def __init__( self, database, user_id, rate_plan ):
    self.database = database
    self.user_id = user_id
    self.rate_plan = int( rate_plan )

    self.set_plan()
    self.database.commit()

  def set_plan( self ):
    user = self.database.load( User, self.user_id )

    if not user:
      print "user id %s unknown" % self.user_id
      sys.exit( 1 )

    user.rate_plan = self.rate_plan
    self.database.save( user )

def main( args ):
  database = Database()
  ranker = Plan_setter( database, *args )


if __name__ == "__main__":
  args = sys.argv[ 1: ]

  if len( args ) != 2:
    print "usage: %s user_id rate_plan_index" % sys.argv[ 0 ]
    sys.exit( 1 )

  main( args )
