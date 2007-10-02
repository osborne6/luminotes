#!/usr/bin/python2.5

import os
import os.path
import psycopg2 as psycopg
from controller.Database import Database
from controller.Scheduler import Scheduler


def quote( value ):
  if value is None:
    return "null"

  value = unicode( value )
  return "'%s'" % value.replace( "'", "''" ).replace( "\\", r"\\\\" )


class Dumper( object ):
  def __init__( self, scheduler, database ):
    self.scheduler = scheduler
    self.database = database

    self.conn = psycopg.connect( "dbname=luminotes user=luminotes password=dev" )
    self.cursor = self.conn.cursor()

    thread = self.dump_database()
    self.scheduler.add( thread )
    self.scheduler.wait_for( thread )

  def dump_database( self ):
    inserts = set()

    for key in self.database._Database__db.keys():
      if not self.database._Database__db.get( key ):
        continue

      self.database.load( key, self.scheduler.thread )
      value = ( yield Scheduler.SLEEP )

      class_name = value.__class__.__name__

      if class_name == "Notebook":
        if ( value.object_id, value.revision ) in inserts: continue
        inserts.add( ( value.object_id, value.revision ) )

        self.cursor.execute(
          "insert into notebook " +
          "( id, revision, name, trash_id ) " +
          "values ( %s, %s, %s, %s );" %
          ( quote( value.object_id ), quote( value.revision ), quote( value.name ), quote( value.trash and value.trash.object_id or "null" ) )
        )
      elif class_name == "Note":
        if ( value.object_id, value.revision ) in inserts: continue
        inserts.add( ( value.object_id, value.revision ) )

        self.cursor.execute(
          "insert into note " +
          "( id, revision, title, contents, notebook_id, startup, deleted_from_id, rank ) " +
          "values ( %s, %s, %s, %s, %s, %s, %s, %s );" %
          ( quote( value.object_id ), quote( value.revision ), quote( value.title ), quote( value.contents ), quote( None ), quote( None ), quote( value.deleted_from ), quote( None ) )
        )
        # TODO: need to set notebook_id field
        # TODO: need to set startup field
        # TODO: need to set rank field based on startup_notes ordering
      elif class_name == "User":
        if value.username == None: continue

        if ( value.object_id, value.revision ) in inserts: continue
        inserts.add( ( value.object_id, value.revision ) )

        self.cursor.execute(
          "insert into luminotes_user " +
          "( id, revision, username, salt, password_hash, email_address, storage_bytes, rate_plan ) " +
          "values ( %s, %s, %s, %s, %s, %s, %s, %s );" %
          ( quote( value.object_id ), quote( value.revision ), quote( value.username ), quote( value._User__salt ), quote( value._User__password_hash ), quote( value.email_address ), value.storage_bytes, value.rate_plan )
        )
        for notebook in value.notebooks:
          if notebook is None: continue

          read_only = ( notebook.__class__.__name__ == "Read_only_notebook" )
          if read_only:
            notebook_id = notebook._Read_only_notebook__wrapped.object_id
          else:
            notebook_id = notebook.object_id

          if ( value.object_id, notebook_id ) in inserts: continue
          inserts.add( ( value.object_id, notebook_id ) )

          self.cursor.execute(
            "insert into user_notebook " +
            "( user_id, notebook_id, read_write ) " +
            "values ( %s, %s, %s );" %
            ( quote( value.object_id ), quote( notebook_id ),
              quote( read_only and "f" or "t" ) )
          )
      elif class_name == "Read_only_notebook":
        pass
      elif class_name == "Password_reset":
        if value.redeemed == True: continue

        if ( value.object_id, value.revision ) in inserts: continue
        inserts.add( ( value.object_id, value.revision ) )

        self.cursor.execute(
          "insert into password_reset " +
          "( id, email_address, redeemed ) " +
          "values ( %s, %s, %s );" %
          ( quote( value.object_id ), quote( value.email_address ), quote( value.redeemed and "t" or "f" ) )
        )
      elif class_name == "User_list":
        pass
      else:
        raise Exception( "Unconverted value of type %s" % class_name )

    self.conn.commit()
    yield None


def main():
  scheduler = Scheduler()
  database = Database( scheduler, "data.db" )
  initializer = Dumper( scheduler, database )
  scheduler.wait_until_idle()


if __name__ == "__main__":
  main()
