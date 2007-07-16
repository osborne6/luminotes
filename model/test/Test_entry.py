from model.Entry import Entry


class Test_entry( object ):
  def setUp( self ):
    self.object_id = 17
    self.title = u"title goes here"
    self.contents = u"<h3>%s</h3>blah" % self.title

    self.entry = Entry( self.object_id, self.contents )

  def test_create( self ):
    assert self.entry.object_id == self.object_id
    assert self.entry.contents == self.contents
    assert self.entry.title == self.title

  def test_set_contents( self ):
    new_title = u"new title"
    new_contents = u"<h3>%s</h3>new blah" % new_title
    previous_revision = self.entry.revision

    self.entry.contents = new_contents

    assert self.entry.contents == new_contents
    assert self.entry.title == new_title
    assert self.entry.revision > previous_revision

  def test_set_contents_with_html_title( self ):
    new_title = u"new title"
    new_contents = u"<h3>%s<br/></h3>new blah" % new_title
    previous_revision = self.entry.revision

    self.entry.contents = new_contents

    assert self.entry.contents == new_contents
    assert self.entry.title == new_title
    assert self.entry.revision > previous_revision

  def test_to_dict( self ):
    d = self.entry.to_dict()

    assert d.get( "contents" ) == self.contents
    assert d.get( "title" ) == self.title

