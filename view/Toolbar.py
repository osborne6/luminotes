from Tags import P, Div, A, Input, Span, Br
from model.Notebook import Notebook


class Toolbar( Div ):
  def __init__( self, notebook, hide_toolbar = False, note_word = None ):
    Div.__init__(
      self,
      Div(
        P(
          Div( Input(
            type = u"image",
            id = u"newNote", title = u"new %s [ctrl-N]" % ( note_word or u"note" ),
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
          # Notebook.READ_WRITE_FOR_OWN_NOTES should not have a file upload button
          ( notebook.read_write == Notebook.READ_WRITE ) and Div( Input(
            type = u"image",
            id = u"attachFile", title = u"attach file or image",
            src = u"/static/images/toolbar/attach_button.png",
            width = u"40", height = u"40",
            class_ = "image_button",
          ) ) or None,
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
            id = u"strikethrough", title = u"strikethrough [ctrl-S]",
            src = u"/static/images/toolbar/strikethrough_button.png",
            width = u"40", height = u"40",
            class_ = "image_button",
          ) ),
          Div( Input(
            type = u"image",
            id = u"title", title = u"title",
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
      Span( id = "strikethrough_button_hover_preload" ),
      Span( id = "title_button_hover_preload" ),
      Span( id = "bullet_list_button_hover_preload" ),
      Span( id = "numbered_list_button_hover_preload" ),

      Span( id = "new_note_button_down_hover_preload" ),
      Span( id = "link_button_down_hover_preload" ),
      Span( id = "attach_button_down_hover_preload" ),
      Span( id = "bold_button_down_hover_preload" ),
      Span( id = "italic_button_down_hover_preload" ),
      Span( id = "underline_button_down_hover_preload" ),
      Span( id = "strikethrough_button_down_hover_preload" ),
      Span( id = "title_button_down_hover_preload" ),
      Span( id = "bullet_list_button_down_hover_preload" ),
      Span( id = "numbered_list_button_down_hover_preload" ),

      Span( id = "new_note_button_down_preload" ),
      Span( id = "link_button_down_preload" ),
      Span( id = "attach_button_down_preload" ),
      Span( id = "bold_button_down_preload" ),
      Span( id = "italic_button_down_preload" ),
      Span( id = "underline_button_down_preload" ),
      Span( id = "strikethrough_button_down_preload" ),
      Span( id = "title_button_down_preload" ),
      Span( id = "bullet_list_button_down_preload" ),
      Span( id = "numbered_list_button_down_preload" ),

      id = u"toolbar",
      class_ = hide_toolbar and u"undisplayed" or None,
    )
