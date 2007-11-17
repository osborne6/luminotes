from Tags import Div, Span, H4, A
from Rounded_div import Rounded_div


class Link_area( Div ):
  def __init__( self, notebooks, notebook, total_notes_count, parent_id, notebook_path, user ):
    linked_notebooks = [ nb for nb in notebooks if nb.read_write and nb.name not in ( u"trash" ) ]

    Div.__init__(
      self,
      Div(
        H4( u"this notebook" ),
        ( parent_id is None ) and Div(
          A(
            u"all notes",
            href = u"#",
            id = u"all_notes_link",
            title = u"View a list of all notes in this notebook.",
          ),
          Span(
            Span( total_notes_count, id = u"total_notes_count" ), u"total",
            class_ = u"small_text",
          ),
          class_ = u"link_area_item",
        ) or None,

        ( notebook.name != u"Luminotes" ) and Div(
          A(
            u"download as html",
            href = u"/notebooks/download_html/%s" % notebook.object_id,
            id = u"download_html_link",
            title = u"Download a stand-alone copy of the entire wiki notebook.",
          ),
          class_ = u"link_area_item",
        ) or None,

        ( notebook.name == u"Luminotes blog" ) and Div (
          A(
            u"subscribe to rss",
            href = u"%s?rss" % notebook_path,
            id = u"rss link",
            title = u"Subscribe to the RSS feed for the Luminotes blog.",
          ),
          class_ = u"link_area_item",
        ) or None,

        notebook.read_write and Span(
          ( notebook.name != u"trash" ) and Div(
            A(
              u"rename notebook",
              href = u"#",
              id = u"rename_notebook_link",
              title = u"Change the name of this notebook.",
            ),
            class_ = u"link_area_item",
          ) or None,

          ( notebook.name != u"trash" ) and Div(
            A(
              u"delete notebook",
              href = u"#",
              id = u"delete_notebook_link",
              title = u"Move this notebook to the trash.",
            ),
            class_ = u"link_area_item",
          ) or None,

          notebook.trash_id and Div(
            A(
              u"trash",
              href = u"/notebooks/%s?parent_id=%s" % ( notebook.trash_id, notebook.object_id ),
              id = u"trash_link",
              title = u"Look here for notes you've deleted.",
            ),
            class_ = u"link_area_item",
          ) or None,

          ( notebook.name == u"trash" ) and Rounded_div(
            u"trash_notebook",
            A(
              u"trash",
              href = u"#",
              id = u"trash_link",
              title = u"Look here for notes you've deleted.",
            ),
            class_ = u"link_area_item",
          ) or None,
        ) or None,

        id = u"this_notebook_area",
      ),

      Div(
        ( len( linked_notebooks ) > 0 ) and H4( u"notebooks" ) or None,
        [ ( nb.object_id == notebook.object_id ) and Rounded_div(
          u"current_notebook",
          A(
            nb.name,
            href = u"/notebooks/%s" % nb.object_id,
            id = u"notebook_%s" % nb.object_id,
          ),
          class_ = u"link_area_item",
        ) or
        Div(
          A(
            nb.name,
            href = u"/notebooks/%s" % nb.object_id,
            id = u"notebook_%s" % nb.object_id,
          ),
          class_ = u"link_area_item",
        ) for nb in linked_notebooks ],
        ( user.username != u"anonymous" ) and Div(
          A(
            u"add new notebook",
            href = u"#",
            id = u"add_notebook_link",
            title = u"Create a new wiki notebook.",
          ),
          class_ = u"link_area_item",
        ) or None,
        id = u"notebooks_area"
      ),

      Div(
        id = u"storage_usage_area",
      ),
      id = u"link_area",
    )
