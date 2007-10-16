from copy import copy


class Stub_database( object ):
  def __init__( self, connection = None ):
    # map of object id to list of saved objects (presumably in increasing order of revisions)
    self.objects = {}
    self.user_notebook = {} # map of user_id to ( notebook_id, read_write )
    self.last_saved_obj = None
    self.__next_id = 0

  def save( self, obj, commit = False ):
    self.last_saved_obj = obj
    if obj.object_id in self.objects:
      self.objects[ obj.object_id ].append( copy( obj ) )
    else:
      self.objects[ obj.object_id ] = [ copy( obj ) ]

  def load( self, Object_type, object_id, revision = None ):
    obj_list = self.objects.get( object_id )

    if not obj_list:
      return None

    # if a particular revision wasn't requested, just return the most recently saved object
    # matching the given object_id
    if revision is None:
      if not isinstance( obj_list[ -1 ], Object_type ):
        return None
      return copy( obj_list[ -1 ] )

    # a particular revision was requested, so pick it out of the objects matching the given id
    matching_objs = [ obj for obj in obj_list if str( obj.revision ) == str( revision ) ]
    if len( matching_objs ) > 0:
      if not isinstance( matching_objs[ -1 ], Object_type ):
        return None
      return copy( matching_objs[ -1 ] )

    return None

  def select_one( self, Object_type, sql_command ):
    if callable( sql_command ):
      result = sql_command( self )
      if isinstance( result, list ):
        if len( result ) == 0: return None
        return result[ 0 ]
      return result

    raise NotImplementedError( sql_command )

  def select_many( self, Object_type, sql_command ):
    if callable( sql_command ):
      result = sql_command( self )
      if isinstance( result, list ):
        return result
      return [ result ]

    raise NotImplementedError( sql_command )

  def execute( self, sql_command, commit = False ):
    if callable( sql_command ):
      return sql_command( self )

    raise NotImplementedError( sql_command )

  def next_id( self, Object_type, commit = True ):
    self.__next_id += 1
    return unicode( self.__next_id )

  def commit( self ):
    pass

  def close( self ):
    pass
