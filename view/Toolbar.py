from Tags import P, Div, A, Input, Span, Br
from model.Notebook import Notebook


class Toolbar( Div ):
  def __init__( self, notebook, hide_toolbar = False, note_word = None ):
    Div.__init__(
      self,
      Div(
        P(
          Div( Input(
            type = u"button",
            id = u"newNote", title = u"make a new %s [ctrl-M]" % ( note_word or u"note" ),
            class_ = "image_button",
          ), class_ = u"button_background" ),
          Div( Input(
            type = u"button",
            id = u"createLink", title = u"link [ctrl-L]",
            src = u"/static/images/toolbar/link_button.png",
            class_ = "image_button",
          ), class_ = u"button_background" ),
          # Notebook.READ_WRITE_FOR_OWN_NOTES should not have a file upload button
          ( notebook.read_write == Notebook.READ_WRITE ) and Div( Input(
            type = u"button",
            id = u"attachFile", title = u"attach file or image",
            src = u"/static/images/toolbar/attach_button.png",
            class_ = "image_button",
          ), class_ = u"button_background" ) or None,
        ),
        P(
          Div( Input(
            type = u"button",
            id = u"bold", title = u"bold [ctrl-B]",
            src = u"/static/images/toolbar/bold_button.png",
            class_ = "image_button",
          ), class_ = u"button_background" ),
          Div( Input(
            type = u"button",
            id = u"italic", title = u"italic [ctrl-I]",
            src = u"/static/images/toolbar/italic_button.png",
            class_ = "image_button",
          ), class_ = u"button_background" ),
          Div( Input(
            type = u"button",
            id = u"underline", title = u"underline [ctrl-U]",
            src = u"/static/images/toolbar/underline_button.png",
            class_ = "image_button",
          ), class_ = u"button_background" ),
          Div( Input(
            type = u"button",
            id = u"strikethrough", title = u"strikethrough [ctrl-S]",
            src = u"/static/images/toolbar/strikethrough_button.png",
            class_ = "image_button",
          ), class_ = u"button_background" ),
          Div( Input(
            type = u"button",
            id = u"font", title = u"font",
            src = u"/static/images/toolbar/font_button.png",
            class_ = "image_button",
          ), class_ = u"button_background" ),
          Div( Input(
            type = u"button",
            id = u"title", title = u"title",
            src = u"/static/images/toolbar/title_button.png",
            class_ = "image_button",
          ), class_ = u"button_background" ),
        ),
        P(
          Div( Input(
            type = u"button",
            id = u"insertUnorderedList", title = u"bullet list [ctrl-period]",
            src = u"/static/images/toolbar/bullet_list_button.png",
            class_ = "image_button",
          ), class_ = u"button_background" ),
          Div( Input(
            type = u"button",
            id = u"insertOrderedList", title = u"numbered list [ctrl-1]",
            src = u"/static/images/toolbar/numbered_list_button.png",
            class_ = "image_button",
          ), class_ = u"button_background" ),
        ),
        class_ = u"button_wrapper",
      ),

      id = u"toolbar",
      class_ = hide_toolbar and u"undisplayed" or None,
    )
