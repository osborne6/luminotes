from pytz import utc
from datetime import datetime, timedelta
from model.Note import Note


class Test_note( object ):
  def setUp( self ):
    self.object_id = u"17"
    self.title = u"title goes here"
    self.contents = u"<h3>%s</h3>blah" % self.title
    self.summary = None
    self.notebook_id = u"18"
    self.startup = False
    self.rank = 17.5
    self.user_id = u"me"
    self.creation = datetime.now()
    self.delta = timedelta( seconds = 1 )

    self.note = Note.create( self.object_id, self.contents, self.notebook_id, self.startup, self.rank, self.user_id, self.creation, self.summary )

  def test_create( self ):
    assert self.note.object_id == self.object_id
    assert datetime.now( tz = utc ) - self.note.revision < self.delta
    assert self.note.contents == self.contents
    assert self.note.summary == None
    assert self.note.title == self.title
    assert self.note.notebook_id == self.notebook_id
    assert self.note.startup == self.startup
    assert self.note.deleted_from_id == None
    assert self.note.rank == self.rank
    assert self.note.user_id == self.user_id
    assert self.note.creation == self.creation

  def test_set_contents( self ):
    new_title = u"new title"
    new_contents = u"<h3>%s</h3>new blah" % new_title
    previous_revision = self.note.revision

    self.note.contents = new_contents

    assert self.note.revision > previous_revision
    assert self.note.contents == new_contents
    assert self.note.summary == None
    assert self.note.title == new_title
    assert self.note.notebook_id == self.notebook_id
    assert self.note.startup == self.startup
    assert self.note.deleted_from_id == None
    assert self.note.rank == self.rank
    assert self.note.user_id == self.user_id
    assert self.note.creation == self.creation

  def test_set_contents_with_html_title( self ):
    new_title = u"new title"
    new_contents = u"<h3>new<br /> title</h3>new blah"
    previous_revision = self.note.revision

    self.note.contents = new_contents

    # html should be stripped out of the title
    assert self.note.revision > previous_revision
    assert self.note.contents == new_contents
    assert self.note.summary == None
    assert self.note.title == new_title
    assert self.note.notebook_id == self.notebook_id
    assert self.note.startup == self.startup
    assert self.note.deleted_from_id == None
    assert self.note.rank == self.rank
    assert self.note.user_id == self.user_id
    assert self.note.creation == self.creation

  def test_set_contents_with_multiple_titles( self ):
    new_title = u"new title"
    new_contents = u"<h3>new<br /> title</h3>new blah<h3>other title</h3>hmm"
    previous_revision = self.note.revision

    self.note.contents = new_contents

    # should only use the first title
    assert self.note.revision > previous_revision
    assert self.note.contents == new_contents
    assert self.note.summary == None
    assert self.note.title == new_title
    assert self.note.notebook_id == self.notebook_id
    assert self.note.startup == self.startup
    assert self.note.deleted_from_id == None
    assert self.note.rank == self.rank
    assert self.note.user_id == self.user_id
    assert self.note.creation == self.creation

  def test_set_summary( self ):
    summary = u"summary goes here..."
    original_revision = self.note.revision

    self.note.summary = summary

    assert self.note.revision == original_revision
    assert self.note.contents == self.contents
    assert self.note.summary == summary
    assert self.note.title == self.title
    assert self.note.notebook_id == self.notebook_id
    assert self.note.startup == self.startup
    assert self.note.deleted_from_id == None
    assert self.note.rank == self.rank
    assert self.note.user_id == self.user_id
    assert self.note.creation == self.creation

  def test_set_notebook_id( self ):
    previous_revision = self.note.revision
    self.note.notebook_id = u"54"

    assert self.note.revision > previous_revision
    assert self.note.notebook_id == u"54"

  def test_set_startup( self ):
    previous_revision = self.note.revision
    self.note.startup = True

    assert self.note.revision > previous_revision
    assert self.note.startup == True

  def test_set_deleted_from_id( self ):
    previous_revision = self.note.revision
    self.note.deleted_from_id = u"55"

    assert self.note.revision > previous_revision
    assert self.note.deleted_from_id == u"55"

  def test_set_rank( self ):
    previous_revision = self.note.revision
    self.note.rank = 5

    assert self.note.revision > previous_revision
    assert self.note.rank == 5

  def test_set_user_id( self ):
    previous_revision = self.note.revision
    self.note.user_id = u"5"

    assert self.note.revision > previous_revision
    assert self.note.user_id == u"5"

  def test_to_dict( self ):
    d = self.note.to_dict()

    assert d.get( "object_id" ) == self.note.object_id
    assert datetime.now( tz = utc ) - d.get( "revision" ) < self.delta
    assert d.get( "contents" ) == self.contents
    assert d.get( "summary" ) == self.summary
    assert d.get( "title" ) == self.title
    assert d.get( "deleted_from_id" ) == None
    assert d.get( "user_id" ) == self.user_id
    assert d.get( "creation" ) == self.note.creation


class Test_note_blank( Test_note ):
  def setUp( self ):
    self.object_id = u"17"
    self.title = None
    self.contents = None
    self.summary = None
    self.notebook_id = None
    self.startup = False
    self.rank = None
    self.user_id = None
    self.creation = None
    self.delta = timedelta( seconds = 1 )

    self.note = Note.create( self.object_id )

  def test_create( self ):
    assert self.note.object_id == self.object_id
    assert datetime.now( tz = utc ) - self.note.revision < self.delta
    assert self.note.contents == None
    assert self.note.summary == None
    assert self.note.title == None
    assert self.note.notebook_id == None
    assert self.note.startup == False
    assert self.note.deleted_from_id == None
    assert self.note.rank == None
    assert self.note.user_id == None
    assert self.note.creation == None
