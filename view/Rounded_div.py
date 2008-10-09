from Tags import Div


class Rounded_div( Div ):
  def __init__( self, image_name, *args, **kwargs ):
    # if no corners were specified, assumed all corners should be rounded
    corners = kwargs.pop( "corners", [] )
    if len( corners ) == 0:
      corners = ( u"tl", u"tr", u"bl", u"br" )

    div = Div(
      *args,
      **kwargs
    )

    for corner in corners:
      div = Div(
        div,
        class_ = u"%s_%s" % ( image_name, corner ),
      )

    Div.__init__(
      self,
      div,
      id = u"%s_wrapper" % ( kwargs.get( u"id" ) or image_name ),
      class_ = u"%s_color" % image_name,
    )
