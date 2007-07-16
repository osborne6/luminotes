from datetime import datetime


class Persistent( object ):
  def __init__( self, object_id, secondary_id = None ):
    self.__object_id = object_id
    self.__secondary_id = secondary_id
    self.__revision = datetime.now()

  def update_revision( self ):
    self.__revision = datetime.now()

  def revision_id( self ):
    return "%s %s" % ( self.__object_id, self.__revision )

  @staticmethod
  def make_revision_id( object_id, revision ):
    return "%s %s" % ( object_id, revision )

  def to_dict( self ):
    return dict(
      object_id = self.__object_id,
      revision = self.__revision,
    )

  object_id = property( lambda self: self.__object_id )
  secondary_id = property( lambda self: self.__secondary_id )
  revision = property( lambda self: self.__revision )
