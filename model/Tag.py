from Persistent import Persistent, quote


class Tag( Persistent ):
  """
  A tag for a note or a notebook.
  """
  def __init__( self, object_id, revision = None, notebook_id = None, user_id = None, name = None, description = None, value = None ):
    """
    Create a Tag with the given id.

    @type object_id: unicode
    @param object_id: id of the Tag
    @type revision: datetime or NoneType
    @param revision: revision timestamp of the object (optional, defaults to now)
    @type notebook_id: unicode or NoneType
    @param notebook_id: id of the notebook whose namespace this tag is in, if any
    @type user_id: unicode or NoneType
    @param user_id: id of the user who most recently updated this tag, if any
    @type name: unicode or NoneType
    @param name: name of the tag (optional)
    @type description: unicode or NoneType
    @param description: brief description of the tag (optional)
    @type value: unicode or NoneType
    @param value: per-note or per-notebook value of the tag (optional)
    @rtype: Tag
    @return: newly constructed Tag
    """
    Persistent.__init__( self, object_id, revision )
    self.__notebook_id = notebook_id
    self.__user_id = user_id
    self.__name = name
    self.__description = description
    self.__value = value

  @staticmethod
  def create( object_id, notebook_id = None, user_id = None, name = None, description = None, value = None ):
    """
    Convenience constructor for creating a new Tag.

    @type object_id: unicode
    @param object_id: id of the Tag
    @type notebook_id: unicode or NoneType
    @param notebook_id: id of the notebook whose namespace this tag is in, if any
    @type user_id: unicode or NoneType
    @param user_id: id of the user who most recently updated this tag, if any
    @type name: unicode or NoneType
    @param name: name of the tag (optional)
    @type description: unicode or NoneType
    @param description: brief description of the tag (optional)
    @type value: unicode or NoneType
    @param value: per-note or per-notebook value of the tag (optional)
    @rtype: Tag
    @return: newly constructed Tag
    """
    return Tag( object_id, notebook_id = notebook_id, user_id = user_id, name = name, description = description, value = value )

  @staticmethod
  def sql_load( object_id, revision = None ):
    # Tags don't store old revisions
    if revision:
      raise NotImplementedError()

    return \
      """
      select
        tag.id, tag.revision, tag.notebook_id, tag.user_id, tag.name, tag.description
      from
        tag
      where
        tag.id = %s;
      """ % quote( object_id )

  @staticmethod
  def sql_load_by_name( name, notebook_id = None, user_id = None ):
    if notebook_id:
      notebook_id_clause = " and tag.notebook_id = %s" % quote( notebook_id )
    else:
      notebook_id_clause = ""

    if user_id:
      user_id_clause = " and tag.user_id = %s" % quote( user_id )
    else:
      user_id_clause = ""

    return \
      """
      select
        tag.id, tag.revision, tag.notebook_id, tag.user_id, tag.name, tag.description
      from
        tag
      where
        tag.name = %s%s%s;
      """ % ( quote( name ), notebook_id_clause, user_id_clause )

  @staticmethod
  def sql_id_exists( object_id, revision = None ):
    if revision:
      raise NotImplementedError()

    return "select id from tag where id = %s;" % quote( object_id )

  def sql_exists( self ):
    return Tag.sql_id_exists( self.object_id )

  def sql_create( self ):
    return "insert into tag ( id, revision, notebook_id, user_id, name, description ) values ( %s, %s, %s, %s, %s, %s );" % \
    ( quote( self.object_id ), quote( self.revision ), quote( self.__notebook_id ),
      quote( self.__user_id ), quote( self.__name ), quote( self.__description ) )

  def sql_update( self ):
    return "update tag set revision = %s, notebook_id = %s, user_id = %s, name = %s, description = %s where id = %s;" % \
    ( quote( self.revision ), quote( self.__notebook_id ), quote( self.__user_id ),
      quote( self.__name ), quote( self.__description ), quote( self.object_id ) )

  def sql_delete( self ):
    return "delete from tag where id = %s;" % quote( self.object_id )

  def to_dict( self ):
    d = Persistent.to_dict( self )
    d.update( dict(
      notebook_id = self.__notebook_id,
      user_id = self.__user_id,
      name = self.__name,
      description = self.__description,
      value = self.__value,
    ) )

    return d

  notebook_id = property( lambda self: self.__notebook_id )
  user_id = property( lambda self: self.__user_id )
  name = property( lambda self: self.__name )
  description = property( lambda self: self.__description )
  value = property( lambda self: self.__value )
