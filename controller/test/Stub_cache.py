class Stub_cache( object ):
  def __init__( self ):
    self.__objects = {}

  def get( self, key ):
    return self.__objects.get( key )

  def set( self, key, value ):
    self.__objects[ key ] = value

  def delete( self, key ):
    if key in self.__objects:
      del( self.__objects[ key ] )
