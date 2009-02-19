# -*- coding: utf8 -*-

import csv
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


class Test_export_csv( object ):
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

  def test_export_csv( self, note_contents = None ):
    if not note_contents:
      note_contents = u"<h3>blah</h3>foo"

    note3 = Note.create( self.database.next_id( Note ), note_contents, notebook_id = self.notebook.object_id, user_id = self.user.object_id )
    self.database.save( note3 )
    response_headers = {}
    expected_notes = ( self.note1, self.note2, note3 )

    result = invoke(
      "export",
      "csv",
      self.database,
      self.notebook,
      expected_notes,
      response_headers,
    )

    assert response_headers
    assert response_headers[ u"Content-Type" ] == u"text/csv;charset=utf-8"
    assert response_headers[ u"Content-Disposition" ] == 'attachment; filename=%s.csv' % self.notebook.friendly_id

    assert isinstance( result, types.GeneratorType )
    pieces = []

    for piece in result:
      pieces.append( piece )

    csv_data = "".join( pieces )
    reader = csv.reader( StringIO( csv_data ) )

    row = reader.next()
    expected_header = [ u"contents", u"title", u"note_id", u"startup", u"username", u"revision_date" ]
    assert row == expected_header

    note_count = 0

    # assert that startup notes come first, then normal notes in descending revision order
    for row in reader:
      assert len( row ) == len( expected_header )
      ( contents, title, note_id, startup, username, revision_date ) = row

      assert note_count < len( expected_notes )
      expected_note = expected_notes[ note_count ]

      assert expected_note
      assert contents.decode( "utf8" ) == expected_note.contents.strip()

      if expected_note.title:
        assert title.decode( "utf8" ) == expected_note.title.strip()
      else:
        assert not title

      assert note_id.decode( "utf8" ) == expected_note.object_id
      assert startup.decode( "utf8" ) == expected_note.startup and u"1" or "0"
      assert username.decode( "utf8" ) == ( expected_note.user_id and self.user.username or u"" )
      assert revision_date.decode( "utf8" ) == unicode( expected_note.revision )

      note_count += 1

    assert note_count == len( expected_notes )

  def test_export_csv_with_unicode( self ):
    self.test_export_csv( note_contents = u"<h3>blah</h3>ümlaut.png" )

  def test_export_csv_without_note_title( self ):
    self.test_export_csv( note_contents = u"there's no title" )

  def test_export_csv_with_trailing_newline_in_title( self ):
    self.test_export_csv( note_contents = u"<h3>blah\n</h3>foo" )

  def test_export_csv_with_trailing_newline_in_contents( self ):
    self.test_export_csv( note_contents = u"<h3>blah</h3>foo\n" )

  def test_export_csv_with_blank_username( self ):
    self.user._User__username = None
    self.database.save( self.user )

    self.test_export_csv( note_contents = u"<h3>blah</h3>foo" )
