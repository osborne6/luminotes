import re
from Tags import Div, Span, H4, A, Table, Tr, Td


class Note_tree_area( Div ):
  LINK_PATTERN = re.compile( u'<a\s+(?:[^>]+\s)?href="[^"]+"[^>]*>', re.IGNORECASE )

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
        self.make_tree(
          [ self.make_item(
            title = note.title,
            link_attributes = u"href=/notebooks/%s?note_id=%s" % ( notebook.object_id, note.object_id ),
            link_class = u"note_tree_link",
            has_children = self.LINK_PATTERN.search( note.contents ),
            root_note_id = note.object_id,
          ) for note in root_notes ],
          tree_id = u"note_tree_area_holder",
        ),
      ),
      Span( id = "tree_arrow_hover_preload" ),
      Span( id = "tree_arrow_down_preload" ),
      Span( id = "tree_arrow_down_hover_preload" ),
      id = u"note_tree_area",
    )

  @staticmethod
  def make_item( title, link_attributes, link_class, has_children = False, root_note_id = None, target = None ):
    return Tr(
      has_children and \
        Td( id = root_note_id and u"note_tree_expander_" + root_note_id or None, class_ = u"tree_expander" ) or
        Td( id = root_note_id and u"note_tree_expander_" + root_note_id or None, class_ = u"tree_expander_empty" ),
      Td(
        u"<a %s%s%s class=%s>%s</a>" % (
            link_attributes,
            root_note_id and u' id="note_tree_link_%s"' % root_note_id or "",
            target and u' target="%s"' % target or "",
            link_class,
            title or u"untitled note",
        ),
      ),
      id = root_note_id and u"note_tree_item_" + root_note_id or None,
      class_ = u"note_tree_item",
    )

  @staticmethod
  def make_tree( items, tree_id = None ):
    return Table(
      items,
      id = tree_id,
    )
