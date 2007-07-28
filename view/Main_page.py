from Page import Page
from Tags import Input, Div, Noscript, H2, H4, A
from Search_form import Search_form
from Link_area import Link_area
from Toolbar import Toolbar


class Main_page( Page ):
  def __init__( self, notebook_id = None, note_id = None ):
    title = None

    Page.__init__(
      self,
      title,
      Input( type = u"hidden", name = u"notebook_id", id = u"notebook_id", value = notebook_id or "" ),
      Input( type = u"hidden", name = u"note_id", id = u"note_id", value = note_id or "" ),
      Div(
        id = u"status_area",
      ),
      Div(
        Link_area( notebook_id ),
        id = u"link_area",
      ),
      Div(
        Toolbar(),
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
            id = u"notes",
          ),
          Noscript(
            u"""
            Luminotes is a personal wiki notebook for organizing your notes and ideas. It also
            happens to require Javascript. So if you'd like to check out this site, please enable
            Javascript in your web browser. Sorry for the inconvenience.
            """,
          ),
          id = u"center_area",
        ),
        id = u"center_and_toolbar_area",
      ),
    )
