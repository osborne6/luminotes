from Page import Page
from Header import Header
from Tags import Link, Div, A, Span


class Product_page( Page ):
  def __init__( self, user, first_notebook, login_url, logout_url, note_title, *nodes ):
    Page.__init__(
      self,
      None, # use the default title
      Link( rel = u"stylesheet", type = u"text/css", href = u"/static/css/header.css" ),
      Link( rel = u"stylesheet", type = u"text/css", href = u"/static/css/product.css" ),

      Header( user, first_notebook, login_url, logout_url, note_title ),

      Span(
        *nodes
      ),

      Div(
        Div(
          Div(
            u"Copyright &copy;2008 Luminotes", u" | ",
            A( u"download", href = u"/download" ), u" | ",
            A( u"contact", href = u"/contact_info" ), u" | ",
            A( u"team", href = u"/meet_the_team" ), u" | ",
            A( u"blog", href = u"/blog" ), u" | ",
            A( u"privacy", href = u"/privacy" ),
            class_ = u"footer_links",
          ),
          class_ = u"wide_center_area",
        ),
        class_ = u"footer",
      ),
    )
