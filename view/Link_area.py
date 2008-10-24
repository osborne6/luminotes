from Tags import Div, P, Span, H4, A, Strong, Img, Input, Br
from Rounded_div import Rounded_div
from Search_form import Search_form
from model.Notebook import Notebook


class Link_area( Div ):
  def __init__( self, notebooks, notebook, parent_id, notebook_path, updates_path, user, rate_plan ):
    linked_notebooks = [ nb for nb in notebooks if
      (
        nb.read_write == Notebook.READ_WRITE or
        ( nb.read_write == Notebook.READ_ONLY and not nb.name.startswith( u"Luminotes" ) )
      ) and
      nb.name not in ( u"trash" ) and
      nb.deleted is False
    ]

    Div.__init__(
      self,
      Div(
        Div(
          H4(
            u"this notebook",
            notebook.read_write != Notebook.READ_ONLY and Input(
              type = u"button",
              class_ = u"note_button small_text",
              id = u"save_button",
              value = u"saved",
              disabled = u"true",
              title = u"save your work",
            ) or None,
            id = u"this_notebook_area_title",
          ),
          Div(
            Search_form(),
            class_ = u"link_area_item",
          ),

          ( rate_plan.get( u"notebook_sharing" ) and notebook.name == u"Luminotes blog" ) and Div(
            A(
              u"subscribe to rss",
              href = u"%s?rss" % notebook_path,
              id = u"blog_rss_link",
              title = u"Subscribe to the RSS feed for the Luminotes blog.",
            ),
            A(
              Img( src = u"/static/images/rss.png", width = u"14", height = u"14", class_ = u"middle_image" ),
              href = u"%s?rss" % notebook_path,
              title = u"Subscribe to the RSS feed for the Luminotes blog.",
            ),
            class_ = u"link_area_item",
          ) or ( updates_path and rate_plan.get( u"notebook_sharing" ) and Div(
            A(
              u"subscribe to rss",
              href = updates_path,
              id = u"notebook_rss_link",
              title = u"Subscribe to the RSS feed for this notebook.",
            ),
            A(
              Img( src = u"/static/images/rss.png", width = u"14", height = u"14", class_ = u"middle_image" ),
              href = updates_path,
              title = u"Subscribe to the RSS feed for this notebook.",
            ),
            class_ = u"link_area_item",
          ) or None ),

          ( notebook.read_write != Notebook.READ_ONLY ) and Div(
            A(
              u"nothing but notes",
              href = u"#",
              id = u"declutter_link",
              title = u"Focus on just your notes without any distractions.",
            ),
            class_ = u"link_area_item",
          ) or None,

          ( notebook.read_write != Notebook.READ_WRITE and notebook.name != u"Luminotes" ) and Div(
            A(
              u"export",
              href = u"#",
              id = u"export_link",
              title = u"Download a stand-alone copy of the entire wiki notebook.",
            ),
            class_ = u"link_area_item",
          ) or None,

          ( notebook.read_write == Notebook.READ_WRITE ) and Span(
            Div(
              A(
                u"import",
                href = u"#",
                id = u"import_link",
                title = u"Import notes from other software into Luminotes.",
              ),
              u"|",
              A(
                u"export",
                href = u"#",
                id = u"export_link",
                title = u"Download a stand-alone copy of the entire wiki notebook.",
              ),
              class_ = u"link_area_item",
            ) or None,

            ( notebook.owner and notebook.name != u"trash" ) and Div(
              A(
                u"rename",
                href = u"#",
                id = u"rename_notebook_link",
                title = u"Change the name of this notebook.",
              ),
              class_ = u"link_area_item",
            ) or None,

            ( notebook.owner and notebook.name != u"trash" ) and Div(
              A(
                u"delete",
                href = u"#",
                id = u"delete_notebook_link",
                title = u"Move this notebook to the trash.",
              ),
              class_ = u"link_area_item",
            ) or None,

            ( notebook.owner and user.username and rate_plan.get( u"notebook_sharing" ) ) and Div(
              A(
                u"share",
                href = u"#",
                id = u"share_notebook_link",
                title = u"Share this notebook with others.",
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
          ( len( linked_notebooks ) > 0 ) and H4(
            u"notebooks",
            Img(
              src = u"/static/images/toolbar/small/new_note_button.png",
              width = u"20", height = u"20",
              id = "new_notebook",
              class_ = u"middle_image",
              title = u"Create a new wiki notebook."
            ),
            id = u"notebooks_area_title",
          ) or None,
          [ ( nb.object_id == notebook.object_id ) and Rounded_div(
            u"current_notebook",
            A(
              nb.name,
              href = u"/notebooks/%s" % nb.object_id,
              id = u"notebook_%s" % nb.object_id,
            ),
            ( len( linked_notebooks ) > 1 ) and Span(
              Img( src = u"/static/images/up_arrow.png", width = u"20", height = u"17", id = u"current_notebook_up" ),
              Img( src = u"/static/images/down_arrow.png", width = u"20", height = u"17", id = u"current_notebook_down" ),
              Span( id = "current_notebook_up_hover_preload" ),
              Span( id = "current_notebook_down_hover_preload" ),
            ) or None,
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
          id = u"notebooks_area"
        ),

        ( user.username is None and notebook_path != "/" ) and P(
          A( u"Download", href = u"/download", class_ = u"hook_action"  ),
          Span( u" or ", class_ = u"hook_action_or" ),
          A( u"Sign up", href = u"/pricing", class_ = u"hook_action"  ), Br(),
          Span( "Get started in seconds.", class_ = u"hook_action_detail" ),
          class_ = u"hook_action_area",
          separator = u"",
        ) or None,

        Div(
          id = u"storage_usage_area",
        ),
        id = u"link_area_holder",
      ),
      id = u"link_area",
    )
