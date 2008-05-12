from Tags import P, Div, A, Input, Span, Br


class Toolbar( Div ):
  def __init__( self, hide_toolbar = False ):
    Div.__init__(
      self,
      Div(
        P(
          Div( Input(
            type = u"image",
            id = u"newNote", title = u"new note [ctrl-N]",
            src = u"/static/images/toolbar/new_note_button.png",
            width = u"40", height = u"40",
            class_ = "image_button",
          ) ),
          Div( Input(
            type = u"image",
            id = u"createLink", title = u"link [ctrl-L]",
            src = u"/static/images/toolbar/link_button.png",
            width = u"40", height = u"40",
            class_ = "image_button",
          ) ),
          Div( Input(
            type = u"image",
            id = u"attachFile", title = u"attach file",
            src = u"/static/images/toolbar/attach_button.png",
            width = u"40", height = u"40",
            class_ = "image_button",
          ) ),
        ),
        P(
          Div( Input(
            type = u"image",
            id = u"bold", title = u"bold [ctrl-B]",
            src = u"/static/images/toolbar/bold_button.png",
            width = u"40", height = u"40",
            class_ = "image_button",
          ) ),
          Div( Input(
            type = u"image",
            id = u"italic", title = u"italic [ctrl-I]",
            src = u"/static/images/toolbar/italic_button.png",
            width = u"40", height = u"40",
            class_ = "image_button",
          ) ),
          Div( Input(
            type = u"image",
            id = u"underline", title = u"underline [ctrl-U]",
            src = u"/static/images/toolbar/underline_button.png",
            width = u"40", height = u"40",
            class_ = "image_button",
          ) ),
          Div( Input(
            type = u"image",
            id = u"title", title = u"title [ctrl-T]",
            src = u"/static/images/toolbar/title_button.png",
            width = u"40", height = u"40",
            class_ = "image_button",
          ) ),
        ),
        P(
          Div( Input(
            type = u"image",
            id = u"insertUnorderedList", title = u"bullet list [ctrl-period]",
            src = u"/static/images/toolbar/bullet_list_button.png",
            width = u"40", height = u"40",
            class_ = "image_button",
          ) ),
          Div( Input(
            type = u"image",
            id = u"insertOrderedList", title = u"numbered list [ctrl-1]",
            src = u"/static/images/toolbar/numbered_list_button.png",
            width = u"40", height = u"40",
            class_ = "image_button",
          ) ),
        ),
        class_ = u"button_wrapper",
      ),

      Span( id = "new_note_button_hover_preload" ),
      Span( id = "link_button_hover_preload" ),
      Span( id = "attach_button_hover_preload" ),
      Span( id = "bold_button_hover_preload" ),
      Span( id = "italic_button_hover_preload" ),
      Span( id = "underline_button_hover_preload" ),
      Span( id = "title_button_hover_preload" ),
      Span( id = "bullet_list_button_hover_preload" ),
      Span( id = "numbered_list_button_hover_preload" ),

      Span( id = "new_note_button_down_hover_preload" ),
      Span( id = "link_button_down_hover_preload" ),
      Span( id = "attach_button_down_hover_preload" ),
      Span( id = "bold_button_down_hover_preload" ),
      Span( id = "italic_button_down_hover_preload" ),
      Span( id = "underline_button_down_hover_preload" ),
      Span( id = "title_button_down_hover_preload" ),
      Span( id = "bullet_list_button_down_hover_preload" ),
      Span( id = "numbered_list_button_down_hover_preload" ),

      Span( id = "new_note_button_down_preload" ),
      Span( id = "link_button_down_preload" ),
      Span( id = "attach_button_down_preload" ),
      Span( id = "bold_button_down_preload" ),
      Span( id = "italic_button_down_preload" ),
      Span( id = "underline_button_down_preload" ),
      Span( id = "title_button_down_preload" ),
      Span( id = "bullet_list_button_down_preload" ),
      Span( id = "numbered_list_button_down_preload" ),

      id = u"toolbar",
      class_ = hide_toolbar and u"undisplayed" or None,
    )
