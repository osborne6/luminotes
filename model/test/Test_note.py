from model.Note import Note


class Test_note( object ):
  def setUp( self ):
    self.object_id = u"17"
    self.title = u"title goes here"
    self.contents = u"<h3>%s</h3>blah" % self.title

    self.note = Note( self.object_id, self.contents )

  def test_create( self ):
    assert self.note.object_id == self.object_id
    assert self.note.contents == self.contents
    assert self.note.title == self.title
    assert self.note.deleted_from == None

  def test_create_blank( self ):
    object_id = u"22"
    blank_note = Note( object_id )

    assert blank_note.object_id == object_id
    assert blank_note.contents == None
    assert blank_note.title == None
    assert blank_note.deleted_from == None

  def test_set_contents( self ):
    new_title = u"new title"
    new_contents = u"<h3>%s</h3>new blah" % new_title
    previous_revision = self.note.revision

    self.note.contents = new_contents

    assert self.note.contents == new_contents
    assert self.note.title == new_title
    assert self.note.deleted_from == None
    assert self.note.revision > previous_revision

  def test_set_contents_with_html_title( self ):
    new_title = u"new title"
    new_contents = u"<h3>new<br /> title</h3>new blah"
    previous_revision = self.note.revision

    self.note.contents = new_contents

    # html should be stripped out of the title
    assert self.note.contents == new_contents
    assert self.note.title == new_title
    assert self.note.deleted_from == None
    assert self.note.revision > previous_revision

  def test_set_contents_with_multiple_titles( self ):
    new_title = u"new title"
    new_contents = u"<h3>new<br /> title</h3>new blah<h3>other title</h3>hmm"
    previous_revision = self.note.revision

    self.note.contents = new_contents

    # should only use the first title
    assert self.note.contents == new_contents
    assert self.note.title == new_title
    assert self.note.deleted_from == None
    assert self.note.revision > previous_revision

  def test_delete( self ):
    previous_revision = self.note.revision
    self.note.deleted_from = u"55"

    assert self.note.deleted_from == u"55"
    assert self.note.revision > previous_revision

  def test_undelete( self ):
    previous_revision = self.note.revision
    self.note.deleted_from = None

    assert self.note.deleted_from == None
    assert self.note.revision > previous_revision

  def test_to_dict( self ):
    d = self.note.to_dict()

    assert d.get( "contents" ) == self.contents
    assert d.get( "title" ) == self.title
    assert d.get( "deleted_from" ) == None
    assert d.get( "object_id" ) == self.note.object_id
    assert d.get( "revision" )
    assert d.get( "revisions_list" )
