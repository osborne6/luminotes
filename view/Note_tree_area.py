import re
from Tags import Div, Span, H4, A


class Note_tree_area( Div ):
  LINK_PATTERN = re.compile( u'<a\s+([^>]+\s)?href="[^"]+"[^>]*>', re.IGNORECASE )

  def __init__( self, toolbar, notebook, root_notes, total_notes_count ):
    Div.__init__(
      self,
      toolbar,
      Div(
        H4( u"notes",
          Span(
            Span( total_notes_count, id = u"total_notes_count" ), u"total",
            class_ = u"small_text link_area_item",
          ),
          id = u"note_tree_area_title",
        ),
        [ Div(
          self.LINK_PATTERN.search( note.contents ) and \
            Div( id = u"note_tree_expander_" + note.object_id, class_ = u"tree_expander" ) or
            Div( id = u"note_tree_expander_" + note.object_id, class_ = u"tree_expander_empty" ),
          A(
            note.title or u"untitled note",
            href = u"/notebooks/%s?note_id=%s" % ( notebook.object_id, note.object_id ),
            id = u"note_tree_link_" + note.object_id,
            class_ = u"note_tree_link",
          ),
          id = u"note_tree_item_" + note.object_id,
          class_ = u"note_tree_item",
        ) for note in root_notes ],
        id = u"note_tree_area_holder",
      ),
      id = u"note_tree_area",
    )
