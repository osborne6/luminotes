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
            class_ = "image_button newNote_large",
          ), class_ = u"button_background" ),
          Div( Input(
            type = u"button",
            id = u"createLink", title = u"link [ctrl-L]",
            class_ = "image_button createLink_large",
          ), class_ = u"button_background" ),
          # Notebook.READ_WRITE_FOR_OWN_NOTES should not have a file upload button
          ( notebook.read_write == Notebook.READ_WRITE ) and Div( Input(
            type = u"button",
            id = u"attachFile", title = u"attach file or image",
            class_ = "image_button attachFile_large",
          ), class_ = u"button_background" ) or None,
        ),
        P(
          Div( Input(
            type = u"button",
            id = u"bold", title = u"bold [ctrl-B]",
            class_ = "image_button bold_large",
          ), class_ = u"button_background" ),
          Div( Input(
            type = u"button",
            id = u"italic", title = u"italic [ctrl-I]",
            class_ = "image_button italic_large",
          ), class_ = u"button_background" ),
          Div( Input(
            type = u"button",
            id = u"underline", title = u"underline [ctrl-U]",
            class_ = "image_button underline_large",
          ), class_ = u"button_background" ),
          Div( Input(
            type = u"button",
            id = u"strikethrough", title = u"strikethrough [ctrl-S]",
            class_ = "image_button strikethrough_large",
          ), class_ = u"button_background" ),
          Div( Input(
            type = u"button",
            id = u"font", title = u"font",
            class_ = "image_button font_large",
          ), class_ = u"button_background" ),
          Div( Input(
            type = u"button",
            id = u"title", title = u"title",
            class_ = "image_button title_large",
          ), class_ = u"button_background" ),
        ),
        P(
          Div( Input(
            type = u"button",
            id = u"insertUnorderedList", title = u"bullet list [ctrl-period]",
            class_ = "image_button insertUnorderedList_large",
          ), class_ = u"button_background" ),
          Div( Input(
            type = u"button",
            id = u"insertOrderedList", title = u"numbered list [ctrl-1]",
            class_ = "image_button insertUnorderedList_large",
          ), class_ = u"button_background" ),
        ),
        class_ = u"button_wrapper",
      ),

      id = u"toolbar",
      class_ = hide_toolbar and u"undisplayed" or None,
    )
