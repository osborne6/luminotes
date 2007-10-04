import warnings
warnings.filterwarnings( "ignore", message = "The sre module is deprecated, please import re." )
from simplejson import JSONEncoder
from datetime import datetime, date


class Json( JSONEncoder ):
  def __init__( self, **kwargs ):
    JSONEncoder.__init__( self )
    self.__kwargs = kwargs

  def __str__( self ):
    return self.encode( self.__kwargs )

  def default( self, obj ):
    """
    Invoked by JSONEncoder.encode() for types that it doesn't know how to encode.
    """
    if isinstance( obj, datetime ) or isinstance( obj, date ):
      return unicode( obj )

    if hasattr( obj, "to_dict" ):
      return obj.to_dict()

    raise TypeError
