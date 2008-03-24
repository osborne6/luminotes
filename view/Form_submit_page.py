from Tags import Html, Head, Body, Script


class Form_submit_page( Html ):
  def __init__( self, form ):
    Html.__init__(
      self,
      Head(),
      Body(
        form,
        Script( # auto-submit the form
          u"document.forms[ 0 ].submit();",
          type = u"text/javascript",
        ),
      ),
    )
