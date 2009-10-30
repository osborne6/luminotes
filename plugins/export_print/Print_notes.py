import re
from view.Tags import Html, Head, Title, Style, Meta, Body, H1, Div, Span, A


class Print_notes( Html ):
  NOTE_LINK_PATTERN = re.compile( u'<a\s+href="[^"]*(?:\/notebooks\/)?[^>]+[?&]note_id=([a-z0-9]*)"[^>]*>', re.IGNORECASE )

  def __init__( self, notebook, notes ):
    relinked_notes = {} # map from note id to relinked note contents

    # relink all note links so they point to named anchors within the page
    for note in notes:
      contents = self.NOTE_LINK_PATTERN.sub( r'<a href="#note_\1">', note.contents )
      contents = contents.replace( u"\u200B", u"" ) # Nuke any placeholder chars.
      relinked_notes[ note.object_id ] = contents

    Html.__init__(
      self,
      Head(
        Style( file( u"static/css/download.css" ).read(), type = u"text/css" ),
        Style( file( u"static/css/print.css" ).read(), type = u"text/css" ),
        Style( u".not_printed { display: none; }", type = u"text/css", media = u"print" ),
        Meta( content = u"text/html; charset=UTF-8", http_equiv = u"content-type" ),
        Title( notebook and notebook.name or notes[ 0 ].title ),
      ),
      Body(
        Div(
          A(
            u"print",
            href = "#",
            onclick = u"window.print(); return false;",
            class_ = "print_link not_printed",
          ),
          notebook and H1( notebook.name ) or None,
          [ Span(
            A( name = u"note_%s" % note.object_id ),
            Div(
              relinked_notes[ note.object_id ],
              class_ = u"note_frame",
            ),
          ) for note in notes ],
          A( "Luminotes.com", href = "http://luminotes.com/" ),
          id = u"center_area",
        ),
        onload = "window.print();",
      ),
    )
