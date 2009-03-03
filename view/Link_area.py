from Tags import Div, P, Span, H4, A, Strong, Img, Br
from Rounded_div import Rounded_div
from model.Notebook import Notebook


class Link_area( Div ):
  def __init__( self, toolbar, notebooks, notebook, parent_id, notebook_path, updates_path, user, rate_plan ):
    linked_notebooks = [ nb for nb in notebooks if
      (
        nb.read_write == Notebook.READ_WRITE or
        ( nb.read_write == Notebook.READ_ONLY and not nb.name.startswith( u"Luminotes" ) )
      ) and
      nb.name not in ( u"trash" ) and
      nb.deleted is False
    ]

    if [ tag for tag in notebook.tags if tag.name == u"forum" ]:
      forum_tag = True
      forum_name = tag.value
      notebook_word = u"discussion"
      note_word = u"post"
    else:
      forum_tag = False
      forum_name = None
      notebook_word = u"notebook"
      note_word = u"note"

    Div.__init__(
      self,
      toolbar,
      ( user.username == u"anonymous" ) and self.forum_link( forum_tag, forum_name ) or None,
      ( user.username != u"anonymous" ) and Div(
        ( notebook_path != u"/" ) and Div(
          H4(
            u"this %s" % notebook_word,
            id = u"this_notebook_area_title",
          ),
          self.forum_link( forum_tag, forum_name ),

          ( rate_plan.get( u"notebook_sharing" ) and notebook.name == u"Luminotes blog" ) and Div(
            A(
              u"follow",
              href = u"%s?rss" % notebook_path,
              id = u"blog_rss_link",
              title = u"Subscribe to the RSS feed for the Luminotes blog.",
            ),
            A(
              Img( src = u"/static/images/rss.png", width = u"14", height = u"14", class_ = u"middle_image padding_left" ),
              href = u"%s?rss" % notebook_path,
              title = u"Subscribe to the RSS feed for the Luminotes blog.",
            ),
            class_ = u"link_area_item",
          ) or ( updates_path and rate_plan.get( u"notebook_sharing" ) and ( not forum_tag ) and Div(
            A(
              u"follow",
              href = updates_path,
              id = u"notebook_rss_link",
              title = u"Subscribe to the RSS feed for this %s." % notebook_word,
            ),
            A(
              Img( src = u"/static/images/rss.png", width = u"14", height = u"14", class_ = u"middle_image padding_left" ),
              href = updates_path,
              title = u"Subscribe to the RSS feed for this %s." % notebook_word,
            ),
            class_ = u"link_area_item",
          ) or None ),

          ( notebook.read_write != Notebook.READ_ONLY ) and Div(
            A(
              u"nothing but %ss" % note_word,
              href = u"#",
              id = u"declutter_link",
              title = u"Focus on just your %ss without any distractions." % note_word,
            ),
            class_ = u"link_area_item",
          ) or None,

          ( notebook.read_write != Notebook.READ_WRITE and notebook.name != u"Luminotes" ) and Div(
            A(
              u"export",
              href = u"#",
              id = u"export_link",
              title = u"Download a stand-alone copy of the entire %s." % notebook_word,
            ),
            class_ = u"link_area_item",
          ) or None,

          ( notebook.read_write != Notebook.READ_WRITE ) and Div(
            A(
              u"print",
              href = u"/notebooks/export?notebook_id=%s&format=print" % notebook.object_id,
              id = u"print_notebook_link",
              target = u"_new",
              title = u"Print this %s." % notebook_word,
             ),
             class_ = u"link_area_item",
          ) or None,

          ( notebook.read_write == Notebook.READ_WRITE ) and Span(
            Div(
              ( notebook.name != u"trash" ) and A(
                u"import",
                href = u"#",
                id = u"import_link",
                title = u"Import %ss from other software into Luminotes." % note_word,
              ) or None,
              ( notebook.name != u"trash" ) and u"|" or None,
              A(
                u"export",
                href = u"#",
                id = u"export_link",
                title = u"Download a stand-alone copy of the entire %s." % notebook_word,
              ),
              class_ = u"link_area_item",
            ) or None,

            ( notebook.name != u"trash" ) and Div(
              notebook.trash_id and A(
                u"trash",
                href = u"/notebooks/%s?parent_id=%s" % ( notebook.trash_id, notebook.object_id ),
                id = u"trash_link",
                title = u"Look here for %ss you've deleted." % note_word,
              ) or None,
              ( notebook.owner and notebook.name != u"trash" and notebook.trash_id ) and u"|" or None,
              ( notebook.owner and notebook.name != u"trash" ) and A(
                u"delete",
                href = u"#",
                id = u"delete_notebook_link",
                title = u"Move this %s to the trash." % notebook_word,
              ) or None,
              class_ = u"link_area_item",
            ) or None,

            ( notebook.owner and notebook.name != u"trash" ) and Div(
              A(
                u"rename",
                href = u"#",
                id = u"rename_notebook_link",
                title = u"Change the name of this %s." % notebook_word,
               ),
               class_ = u"link_area_item",
            ) or None,

            ( notebook.owner and notebook.name != u"trash" and
              user.username and rate_plan.get( u"notebook_sharing" ) ) and Div(
              A(
                u"share",
                href = u"#",
                id = u"share_notebook_link",
                title = u"Share this %s with others." % notebook_word,
              ),
              class_ = u"link_area_item",
            ) or None,

            Div(
              A(
                u"print",
                href = u"/notebooks/export?notebook_id=%s&format=print" % notebook.object_id,
                id = u"print_notebook_link",
                target = u"_new",
                title = u"Print this %s." % notebook_word,
               ),
               class_ = u"link_area_item",
            ) or None,

            ( notebook.name == u"trash" ) and Rounded_div(
              u"trash_notebook",
              A(
                u"trash",
                href = u"#",
                id = u"trash_link",
                title = u"Look here for %ss you've deleted." % note_word,
              ),
              class_ = u"link_area_item",
            ) or None,
          ) or None,

          id = u"this_notebook_area",
        ) or None,

        ( not forum_tag ) and Div(
          ( len( linked_notebooks ) > 0 ) and H4(
            u"notebooks",
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
        ) or None,
        ( not forum_tag ) and Div(
          Img(
            src = u"/static/images/toolbar/small/new_note_button.png",
            width = u"20", height = u"20",
            id = "new_notebook",
            class_ = u"middle_image",
            title = u"Create a new wiki notebook."
          ),
          class_ = u"link_area_item",
        ) or None,

        Div(
          id = u"storage_usage_area",
        ),
        id = u"link_area_holder",
      ) or None,
      id = u"link_area",
    )

  @staticmethod
  def forum_link( forum_tag, forum_name ):
    if not forum_tag:
      return None

    if forum_name == u"blog":
      return Div(
        A( u"Luminotes %s" % forum_name, href = "/blog/" ),
        class_ = u"link_area_item",
      )

    return Div(
      A( u"%s forum" % forum_name, href = "/forums/%s" % forum_name ),
      class_ = u"link_area_item",
    )
