import re
from model.Notebook import Notebook
from Tags import Div, Span, H4, A, Table, Tbody, Tr, Td, Img, P, Br, Input
from Search_form import Search_form


class Note_tree_area( Div ):
  LINK_PATTERN = re.compile( u'<a\s+(?:[^>]+\s)?href="[^"]+"[^>]*>', re.IGNORECASE )

  def __init__( self, notebook, root_notes, recent_notes, total_notes_count, user ):
    tags = [ tag for tag in notebook.tags if tag.name == u"forum" ]

    if tags:
      forum_name = tags[ 0 ].value
      forum_tag = True
    else:
      forum_name = None
      forum_tag = False

    Div.__init__(
      self,
      Div(
        H4(
          forum_tag and u"posts" or u"notes",
          Span(
            Span( total_notes_count, id = u"total_notes_count" ), u"total",
            class_ = u"small_text link_area_item",
          ),
          notebook.read_write != Notebook.READ_ONLY and Input(
            type = u"button",
            class_ = u"note_button small_text",
            id = u"save_button",
            value = u"saved",
            disabled = u"true",
            title = u"save your work",
          ) or None,
          id = u"note_tree_area_title",
        ) or None,
        Div(
          Search_form(),
          class_ = u"link_area_item",
        ),
        forum_tag and Div(
          A( u"%s forum" % forum_name, href = "/forums/%s" % forum_name ),
          class_ = u"link_area_item",
        ) or None,
        ( not forum_tag ) and self.make_tree(
          [ self.make_item(
            title = note.title,
            link_attributes = u'href="/notebooks/%s?note_id=%s"' % ( notebook.object_id, note.object_id ),
            link_class = u"note_tree_link",
            has_children = ( notebook.name != u"trash" ) and self.LINK_PATTERN.search( note.contents ) or False,
            root_note_id = note.object_id,
          ) for note in root_notes ],
          Tr(
            Td(),
            ( notebook.name != u"trash" and notebook.read_write == Notebook.READ_WRITE ) and Td(
              Img(
                src = u"/static/images/toolbar/small/new_note_button.png",
                width = u"20", height = u"20",
                id = u"new_note_tree_link",
                class_ = u"middle_image",
                title = u"Add a note to this note tree."
              ),
              Span( id = u"new_note_tree_link_area" ),
            ) or None,
            id = u"new_note_tree_link_row",
          ) or None,
          tree_id = "note_tree_root_table",
        ) or None,
        ( not forum_tag and recent_notes is not None and notebook.name != u"trash" ) and Span(
          H4( u"recent updates",
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
            navigation = Tbody( Tr( id = "recent_notes_spacer" ), Tr(
              Td(),
              Td(
                A( u"more", href = u"#", id = u"recent_notes_more_link", class_ = u"undisplayed" ),
                A( u"less", href = u"#", id = u"recent_notes_less_link", class_ = u"undisplayed" ),
              ),
            ), id = u"recent_notes_navigation" ),
            tree_id = "recent_notes_table",
          ),
        ) or None,
        ( user.username is None ) and P(
          A( u"Download", href = u"/download", class_ = u"hook_action"  ),
          Span( u" or ", class_ = u"hook_action_or" ),
          A( u"Sign up", href = u"/pricing", class_ = u"hook_action"  ), Br(),
          Span( "Get started in seconds.", class_ = u"hook_action_detail" ),
          class_ = u"hook_action_area",
          separator = u"",
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
        Td( Div( id = root_note_id and u"%s_expander_%s" % ( base_name, root_note_id ) or None, class_ = u"tree_expander" ) ) or
        Td( Div( id = root_note_id and u"%s_expander_%s" % ( base_name, root_note_id ) or None, class_ = u"tree_expander_empty" ) ),
      Td(
        u'<a %s%s%s class="%s">%s</a>' % (
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
  def make_tree( first_node, second_node = None, third_node = None, navigation = None, tree_id = None ):
    return Table(
      Tbody(
        first_node,
        second_node,
        third_node,
        id = tree_id and tree_id + "_body" or None,
      ),
      navigation,
      id = tree_id or None,
      class_ = u"note_tree_table",
    )
