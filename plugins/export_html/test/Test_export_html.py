# -*- coding: utf8 -*-

import types
import cherrypy
from cStringIO import StringIO
from pysqlite2 import dbapi2 as sqlite

from model.User import User
from model.Note import Note
from model.Notebook import Notebook
from controller.Database import Database, Connection_wrapper
from controller.test.Stub_cache import Stub_cache
from plugins.Invoke import invoke


class Test_export_html( object ):
  def setUp( self ):
    self.database = Database(
      Connection_wrapper( sqlite.connect( ":memory:", detect_types = sqlite.PARSE_DECLTYPES, check_same_thread = False ) ),
      cache = Stub_cache(),
    )
    self.database.execute_script( file( "model/schema.sqlite" ).read(), commit = True )

    self.username = u"mulder"
    self.password = u"trustno1"
    self.email_address = u"outthere@example.com"
    self.user = User.create( self.database.next_id( User ), self.username, self.password, self.email_address )
    self.database.save( self.user, commit = False )

    self.trash = Notebook.create( self.database.next_id( Notebook ), u"trash" )
    self.database.save( self.trash, commit = False )
    self.notebook = Notebook.create( self.database.next_id( Notebook ), u"notebook", self.trash.object_id, user_id = self.user.object_id )
    self.database.save( self.notebook, commit = False )

    note_id = self.database.next_id( Note )
    self.note1 = Note.create( note_id, u"<h3>my title</h3>blah", notebook_id = self.notebook.object_id, startup = True, user_id = self.user.object_id )
    self.database.save( self.note1, commit = False )

    note_id = self.database.next_id( Note )
    self.note2 = Note.create( note_id, u"<h3>other title</h3>whee", notebook_id = self.notebook.object_id, user_id = self.user.object_id )
    self.database.save( self.note2, commit = False )

  def test_export_html( self ):
    note3 = Note.create( "55", u"<h3>blah</h3>foo", notebook_id = self.notebook.object_id )
    self.database.save( note3 )
    response_headers = {}
    expected_notes = ( self.note1, self.note2, note3 )

    result = invoke(
      "export",
      "html",
      self.database,
      self.notebook,
      expected_notes,
      response_headers,
    )

    # response headers should be unchanged
    assert response_headers == {}

    notes = result.get( "notes" )
    assert len( notes ) == len( expected_notes )

    # assert that the notes are in the expected order
    for ( note, expected_note ) in zip( notes, expected_notes ):
      assert note.object_id == expected_note.object_id
      assert note.revision == expected_note.revision
      assert note.title == expected_note.title
      assert note.contents == expected_note.contents
      assert note.notebook_id == expected_note.notebook_id
      assert note.startup == expected_note.startup
      assert note.deleted_from_id == expected_note.deleted_from_id
      assert note.rank == expected_note.rank
      assert note.user_id == expected_note.user_id
      assert note.creation == expected_note.creation
