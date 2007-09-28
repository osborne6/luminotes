from Tags import P, Div, A, Input, Span, Br


class Toolbar( Div ):
  def __init__( self ):
    Div.__init__(
      self,
      Div(
        P(
          Div( Div( Span( u"+", class_ = u"toolbar_text" ), id = u"newNote", title = u"new note [ctrl-N]", class_ = u"button" ) ),
          Div( Div(
            Span(
              u"link",
              class_ = u"toolbar_text toolbar_link_text",
            ),
            id = u"createLink", title = u"link [ctrl-L]", class_ = u"button"
          ) ),
        ),
        P(
          Div( Div( Span( u"B", class_ = u"toolbar_text" ), id = u"bold", title = u"bold [ctrl-B]", class_ = u"button" ) ),
          Div( Div( Span( u"I", class_ = u"toolbar_text" ), id = u"italic", title = u"italic [ctrl-I]", class_ = u"button" ) ),
          Div( Div( Span( u"U", class_ = u"toolbar_text" ), id = u"underline", title = u"underline [ctrl-U]", class_ = u"button" ) ),
          Div( Div( Span( u"T", class_ = u"toolbar_text" ), id = u"title", title = u"title [ctrl-T]", class_ = u"button" ) ),
        ),
        P(
          Div( Div(
            Span(
              u"&#149; &#8213;", Br(),
              u"&#149; &#8213;", Br(),
              u"&#149; &#8213;", Br(),
              Br( class_ = "undisplayed" ), # to make IE 6 happy. without this, the last list element is truncated
              class_ = u"toolbar_list_text",
            ),
            id = u"insertUnorderedList", title = u"bullet list [ctrl-period]", class_ = u"button",
          ) ),
          Div( Div(
            Span(
              u"1.&#8213;", Br(),
              u"2.&#8213;", Br(),
              u"3.&#8213;", Br(),
              Br( class_ = "undisplayed" ),
              class_ = u"toolbar_list_text",
            ),
            id = u"insertOrderedList", title = u"numbered list [ctrl-1]", class_ = u"button",
          ) ),
        ),
        class_ = u"button_wrapper",
      ),
      id = u"toolbar",
      class_ = u"undisplayed", # start out as hidden, and then shown in the browser if the current notebook is read-write
    )
