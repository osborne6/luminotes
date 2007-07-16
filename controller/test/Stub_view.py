class Stub_view( object ):
  result = None

  def __init__( self, **kwargs ):
    Stub_view.result = kwargs

  def __str__( self ):
    return ""
