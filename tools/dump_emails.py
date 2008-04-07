#!/usr/bin/python2.4

import os
import os.path
from controller.Database import Database


class Dumper( object ):
  def __init__( self, database ):
    self.database = database

    self.dump_emails()

  def dump_emails( self ):
    email_addresses = self.database.select_many( unicode, u"select distinct email_address from luminotes_user_current where email_address is not null;" )

    for address in email_addresses:
      if address:
        print address


def main( args ):
  database = Database( cache = {} )
  ranker = Dumper( database )


if __name__ == "__main__":
  import sys
  main( sys.argv[ 1: ] )
