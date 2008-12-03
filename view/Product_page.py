from Page import Page
from Header import Header
from Tags import Link, Meta, Div, A, Span, Ul, Li, Br


class Product_page( Page ):
  def __init__( self, user, first_notebook, login_url, logout_url, note_title, *nodes ):
    Page.__init__(
      self,
      ( note_title != "home" ) and note_title or None, # use the default title for the "home" page
      Link( rel = u"stylesheet", type = u"text/css", href = u"/static/css/header.css" ),
      Link( rel = u"stylesheet", type = u"text/css", href = u"/static/css/product.css" ),
      Meta( name = u"description", content = u"Luminotes is a WYSIWYG personal wiki notebook for organizing your notes and ideas." ),
      Meta( name = u"keywords", content = u"note taking, personal wiki, wysiwyg wiki, easy wiki, simple wiki, wiki notebook" ),

      Header( user, first_notebook, login_url, logout_url, note_title ),

      Span(
        *nodes
      ),

      Div(
        Div(
          Div(
            Div(
              Ul(
                Li( u"About", class_ = u"footer_category" ),
                Li( A( u"tour", href = u"/tour" ) ),
                Li( A( u"demo", href = u"/users/demo" ) ),
                Li( A( u"faq", href = u"/faq" ) ),
                Li( A( u"team", href = u"/meet_the_team" ) ),
                Li( A( u"user guide", href = u"/guide" ) ),
                Li( A( u"privacy", href = u"/privacy" ) ),
                class_ = u"footer_list",
              ),
              Ul(
                Li( u"Get Started", class_ = u"footer_category" ),
                Li( A( u"download", href = u"/download" ) ),
                Li( A( u"sign up", href = u"/pricing" ) ),
                Li( A( u"source code", href = u"/source_code" ) ),
                class_ = u"footer_list",
              ),
              Ul(
                Li( u"Community", class_ = u"footer_category" ),
                Li( A( u"contact support", href = u"/contact_info" ) ),
                Li( A( u"discussion forums", href = u"/forums/" ) ),
                Li( A( u"blog", href = u"/blog/" ) ),
                Li( A( u"Facebook group", href = u"http://www.facebook.com/pages/Luminotes-personal-wiki-notebook/17143857741" ) ),
                Li( A( u"Twitter stream", href = u"http://twitter.com/Luminotes" ) ),
                class_ = u"footer_list",
              ),
              Ul(
                Li( u"Copyright &copy;2008 Luminotes" ),
                class_ = u"footer_list wide_footer_list",
              ),
              Br(),
              class_ = u"footer_column",
            ),
            class_ = u"footer_links",
          ),
          class_ = u"wide_center_area",
        ),
        class_ = u"footer",
      ),
    )
