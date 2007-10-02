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
  return "'%s'" % value.replace( "'", "''" ).replace( "\\", "\\\\" )


class Verifier( object ):
  """
  Verifies a conversion of a Luminotes database from bsddb to PostgreSQL that was performed with
  convertdb.py.
  """
  def __init__( self, scheduler, database ):
    self.scheduler = scheduler
    self.database = database

    self.conn = psycopg.connect( "dbname=luminotes user=luminotes password=dev" )
    self.cursor = self.conn.cursor()

    thread = self.verify_database()
    self.scheduler.add( thread )
    self.scheduler.wait_for( thread )

  def verify_database( self ):
    inserts = set()

    for key in self.database._Database__db.keys():
      if not self.database._Database__db.get( key ):
        continue

      self.database.load( key, self.scheduler.thread )
      value = ( yield Scheduler.SLEEP )

      class_name = value.__class__.__name__

      if class_name == "Notebook":
        self.verify_notebook( value )
      elif class_name == "Note":
        self.cursor.execute(
          "select * from note where id = %s and revision = %s;" % ( quote( value.object_id ), quote( value.revision ) )
        )

        for row in self.cursor.fetchmany():
          assert row[ 0 ] == value.object_id
          assert row[ 1 ].replace( tzinfo = None ) == value.revision
          assert row[ 2 ] == ( value.title and value.title.encode( "utf8" ) or None )
          assert row[ 3 ] == ( value.contents and value.contents.encode( "utf8" ) or None )
          # not checking for existence of row 4 (notebook_id), because notes deleted from the trash don't have a notebook id
          assert row[ 5 ] is not None
          assert row[ 6 ] == ( value.deleted_from or None )
          if row[ 5 ] is True: # if this is a startup note, it should have a rank
            assert row[ 7 ] is not None
      elif class_name == "User":
        # skip demo users
        if value.username is None: continue

        self.cursor.execute(
          "select * from luminotes_user where id = %s and revision = %s;" % ( quote( value.object_id ), quote( value.revision ) )
        )

        for row in self.cursor.fetchmany():
          assert row[ 0 ] == value.object_id
          assert row[ 1 ].replace( tzinfo = None ) == value.revision
          assert row[ 2 ] == value.username
          assert row[ 3 ] == value._User__salt
          assert row[ 4 ] == value._User__password_hash
          assert row[ 5 ] == value.email_address
          assert row[ 6 ] == value.storage_bytes
          assert row[ 7 ] == value.rate_plan

        for notebook in value.notebooks:
          if notebook is None: continue

          read_write = ( notebook.__class__.__name__ == "Notebook" )

          self.cursor.execute(
            "select * from user_notebook where user_id = %s and notebook_id = %s;" % ( quote( value.object_id ), quote( notebook.object_id ) )
          )

          for row in self.cursor.fetchmany():
            assert row[ 0 ] == value.object_id
            assert row[ 1 ] == notebook.object_id
            assert row[ 2 ] == read_write

          self.verify_notebook( notebook )

      elif class_name == "Read_only_notebook":
        self.verify_notebook( value._Read_only_notebook__wrapped )
      elif class_name == "Password_reset":
        # skip password resets that are already redeemed
        if value.redeemed: continue

        self.cursor.execute(
          "select * from password_reset where id = %s;" % quote( value.object_id )
        )

        for row in self.cursor.fetchmany():
          assert row[ 0 ] == value.email_address
          assert row[ 1 ] == False
          assert row[ 2 ] == value.object_id
      elif class_name == "User_list":
        pass
      else:
        raise Exception( "Unverified value of type %s" % class_name )

    self.conn.commit()
    yield None

  def verify_notebook( self, value ):
    self.cursor.execute(
      "select * from notebook where id = %s and revision = %s;" % ( quote( value.object_id ), quote( value.revision ) )
    )

    for row in self.cursor.fetchmany():
      assert row[ 0 ] == value.object_id
      assert row[ 1 ].replace( tzinfo = None ) == value.revision
      assert row[ 2 ] == value.name
      if value.trash:
        assert row[ 3 ] == value.trash.object_id
      else:
        assert row[ 3 ] == None

    startup_note_ids = [ note.object_id for note in value.startup_notes ]
    for note in value.notes:
      self.cursor.execute(
        "select * from note where id = %s and revision = %s;" % ( quote( note.object_id ), quote( value.revision ) )
      )

      for row in self.cursor.fetchmany():
        assert row[ 0 ] == note.object_id
        assert row[ 1 ].replace( tzinfo = None ) == note.revision
        assert row[ 2 ] == note.title
        assert row[ 3 ] == note.contents
        assert row[ 4 ] == value.object_id
        assert row[ 5 ] == ( note.object_id in startup_note_ids )
        assert row[ 6 ] == note.deleted_from
        if row[ 5 ] is True: # if this is a startup note, it should have a rank
          assert row[ 7 ] is not None
      
    for note in value.startup_notes:
      self.cursor.execute(
        "select * from note where id = %s and revision = %s order by rank;" % ( quote( note.object_id ), quote( value.revision ) )
      )

      rank = 0
      for row in self.cursor.fetchmany():
        assert row[ 0 ] == note.object_id
        assert row[ 1 ].replace( tzinfo = None ) == note.revision
        assert row[ 2 ] == note.title
        assert row[ 3 ] == note.contents
        assert row[ 4 ] == value.object_id
        assert row[ 5 ] == True
        assert row[ 6 ] == note.deleted_from
        assert row[ 7 ] == rank
        rank += 1


def main():
  scheduler = Scheduler()
  database = Database( scheduler, "data.db" )
  initializer = Verifier( scheduler, database )
  scheduler.wait_until_idle()


if __name__ == "__main__":
  main()
