from Tags import Html, Head, Link, Body, Div, P
from config.Version import VERSION


class Close_page( Html ):
  def __init__( self, script = None ):
    Html.__init__(
      self,
      Head(
        Link( rel = u"stylesheet", type = u"text/css", href = u"/static/css/style.css?%s" % VERSION ),
      ),
      Body(
        Div(
          P(
            u"Luminotes Desktop has been shut down."
          ),
          P(
            u"To start Luminotes again, simply launch it from your Start Menu."
          ),
          id = u"center_area",
        ),
      ),
    )
