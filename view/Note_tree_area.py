from Tags import Div, Span, H4, A


class Note_tree_area( Div ):
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
          Div( class_ = u"tree_expander" ),
          A(
            note.title,
            href = u"/notebooks/%s?note_id=%s" % ( notebook.object_id, note.object_id ),
            id = u"note_tree_link_" + note.object_id,
            class_ = u"note_tree_link",
          ),
          id = u"note_tree_item_" + note.object_id,
          class_ = u"link_area_item",
        ) for note in root_notes ],
        id = u"note_tree_area_holder",
      ),
      id = u"note_tree_area",
    )
