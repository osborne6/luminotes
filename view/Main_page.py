from cgi import escape
from Page import Page
from Tags import Input, Div, Noscript, H2, H4, A
from Search_form import Search_form
from Link_area import Link_area
from Toolbar import Toolbar


class Main_page( Page ):
  def __init__( self, notebook_id = None, note_id = None, parent_id = None, revision = None, note_contents = None ):
    title = None
    note_contents = note_contents and escape( note_contents, quote = True ) or ""

    Page.__init__(
      self,
      title,
      Input( type = u"hidden", name = u"notebook_id", id = u"notebook_id", value = notebook_id or "" ),
      Input( type = u"hidden", name = u"note_id", id = u"note_id", value = note_id or "" ),
      Input( type = u"hidden", name = u"parent_id", id = u"parent_id", value = parent_id or "" ),
      Input( type = u"hidden", name = u"revision", id = u"revision", value = revision or "" ),
      Input( type = u"hidden", name = u"note_contents", id = u"note_contents", value = note_contents ),
      Div(
        id = u"status_area",
      ),
      Toolbar(),
      Div(
        Link_area( notebook_id ),
        id = u"link_area",
      ),
      Div(
        Div(
          Div(
            Div(
              Div(
                id = u"user_area",
              ),
              Div(
                Search_form(),
                id = u"search_area",
              ),
              id = u"search_and_user_area",
            ),
            Div(
              H2( A( u"Luminotes", href = "/" ), class_ = "page_title" ),
              H4( A( u"personal wiki notebook", href = "/" ), class_ = u"page_title" ),
              id = u"title_area",
            ),
            id = u"top_area",
          ),
          Div(
            id = u"notebook_header_area",
            class_ = u"current_notebook_name",
          ),
          Div(
            Div(
              Div(
                id = u"notes",
              ),
              id = u"notebook_background",
            ),
            id = u"notebook_border",
            class_ = u"current_notebook_name",
          ),
          Noscript(
            Div( file( u"static/html/about.html" ).read() ),
            Div( file( u"static/html/features.html" ).read().replace( u"href=", u"disabled=" ) ),
            Div( file( u"static/html/no javascript.html" ).read() ),
          ),
          id = u"center_area",
        ),
        id = u"everything_area",
      ),
    )
