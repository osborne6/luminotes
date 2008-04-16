import re
from Tags import Div, Span, H4, A, Table, Tr, Td


class Note_tree_area( Div ):
  LINK_PATTERN = re.compile( u'<a\s+(?:[^>]+\s)?href="[^"]+"[^>]*>', re.IGNORECASE )

  def __init__( self, toolbar, notebook, root_notes, recent_notes, total_notes_count ):
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
            link_attributes = u'href="/notebooks/%s?note_id=%s"' % ( notebook.object_id, note.object_id ),
            link_class = u"note_tree_link",
            has_children = ( notebook.name != u"trash" ) and self.LINK_PATTERN.search( note.contents ) or False,
            root_note_id = note.object_id,
          ) for note in root_notes ],
          Div(
            ( notebook.name != u"trash" ) and u'Add a note here: Click the "options" tab on a note, then "show on startup".' or None,
            id = "note_tree_instructions",
            class_ = u"small_text link_area_item" + ( ( len( root_notes ) > 0 ) and u" undisplayed" or u"" ),
          ) or None,
          tree_id = "note_tree_root_table",
        ),
        ( recent_notes is not None and notebook.name != u"trash" ) and Span(
          H4( u"recent notes",
            id = u"recent_notes_area_title",
          ),
          self.make_tree(
            Tr( id = "recent_notes_top" ),
            [ self.make_item(
              title = note.title,
              link_attributes = u'href="/notebooks/%s?note_id=%s"' % ( notebook.object_id, note.object_id ),
              link_class = u"recent_note_link",
              has_children = False,
              root_note_id = note.object_id,
              base_name = u"recent_note",
            ) for note in recent_notes ],
            tree_id = "recent_notes_table",
          ),
        ) or None,
        id = u"note_tree_area_holder",
      ),
      Span( id = "tree_arrow_hover_preload" ),
      Span( id = "tree_arrow_down_preload" ),
      Span( id = "tree_arrow_down_hover_preload" ),
      id = u"note_tree_area",
    )

  @staticmethod
  def make_item( title, link_attributes, link_class, has_children = False, root_note_id = None, target = None, base_name = None ):
    if base_name is None:
      base_name = u"note_tree"

    return Tr(
      has_children and \
        Td( id = root_note_id and u"%s_expander_%s" % ( base_name, root_note_id ) or None, class_ = u"tree_expander" ) or
        Td( id = root_note_id and u"%s_expander_%s" % ( base_name, root_note_id ) or None, class_ = u"tree_expander_empty" ),
      Td(
        u"<a %s%s%s class=%s>%s</a>" % (
            link_attributes,
            root_note_id and u' id="%s_link_%s"' % ( base_name, root_note_id ) or "",
            target and u' target="%s"' % target or "",
            link_class,
            title or u"untitled note",
        ),
      ),
      id = root_note_id and u"%s_item_%s" % ( base_name, root_note_id ) or None,
      class_ = u"%s_item" % base_name,
    )

  @staticmethod
  def make_tree( items, other_node = None, tree_id = None ):
    return Table(
      items,
      other_node,
      id = tree_id or None,
      class_ = u"note_tree_table",
    )
