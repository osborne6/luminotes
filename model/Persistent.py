from datetime import datetime


class Persistent( object ):
  def __init__( self, object_id, secondary_id = None ):
    self.__object_id = object_id
    self.__secondary_id = secondary_id
    self.__revision = datetime.now()
    self.__revisions_list = [ self.__revision ]

  def update_revision( self ):
    self.__revision = datetime.now()

    # make a new copy of the list to prevent sharing of this list between different revisions
    self.__revisions_list = self.__revisions_list + [ self.__revision ]

  def revision_id( self ):
    return "%s %s" % ( self.__object_id, self.__revision )

  @staticmethod
  def make_revision_id( object_id, revision ):
    return "%s %s" % ( object_id, revision )

  def full_secondary_id( self ):
    return "%s %s" % ( type( self ).__name__, self.secondary_id )

  def to_dict( self ):
    return dict(
      object_id = self.__object_id,
      revision = self.__revision,
      revisions_list = self.__revisions_list,
    )

  object_id = property( lambda self: self.__object_id )
  secondary_id = property( lambda self: self.__secondary_id )
  revision = property( lambda self: self.__revision )
  revisions_list = property( lambda self: self.__revisions_list )
