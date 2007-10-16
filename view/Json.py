import warnings
warnings.filterwarnings( "ignore", message = "The sre module is deprecated, please import re." )
from simplejson import JSONEncoder
from datetime import datetime, date


class Json( JSONEncoder ):
  def __init__( self, *args, **kwargs ):
    JSONEncoder.__init__( self )

    if args and kwargs:
      raise ValueError( "Please provide either args or kwargs, not both." )

    self.__args = args
    self.__kwargs = kwargs

  def __str__( self ):
    if self.__args:
      if len( self.__args ) == 1:
        return self.encode( self.__args[ 0 ] )
      return self.encode( self.__args )

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
