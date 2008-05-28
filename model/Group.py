from Persistent import Persistent, quote


class Group( Persistent ):
  """
  A group of users, used to represent an organization, department, or team.
  """

  def __init__( self, object_id, revision = None, name = None, admin = None ):
    """
    Create a new group with the given id and name.

    @type object_id: unicode
    @param object_id: id of the group
    @type revision: datetime or NoneType
    @param revision: revision timestamp of the object (optional, defaults to now)
    @type name: unicode or NoneType
    @param name: name of this group (optional)
    @type admin: bool
    @param admin: whether access to this group includes admin capabilities
    @rtype: Group
    @return: newly constructed group
    """
    Persistent.__init__( self, object_id, revision )
    self.__name = name
    self.__admin = admin

  @staticmethod
  def create( object_id, name = None, admin = None ):
    """
    Convenience constructor for creating a new group.

    @type object_id: unicode
    @param object_id: id of the group
    @type name: unicode or NoneType
    @param name: name of this group (optional)
    @type admin: bool
    @param admin: whether access to this group includes admin capabilities
    @rtype: group
    @return: newly constructed group
    """
    return Group( object_id, name = name, admin = admin )

  @staticmethod
  def sql_load( object_id, revision = None ):
    if revision:
      return "select * from luminotes_group where id = %s and revision = %s;" % ( quote( object_id ), quote( revision ) )

    return "select * from luminotes_group_current where id = %s;" % quote( object_id )

  @staticmethod
  def sql_id_exists( object_id, revision = None ):
    if revision:
      return "select id from luminotes_group where id = %s and revision = %s;" % ( quote( object_id ), quote( revision ) )

    return "select id from luminotes_group_current where id = %s;" % quote( object_id )

  def sql_exists( self ):
    return Group.sql_id_exists( self.object_id, self.revision )

  def sql_create( self ):
    return \
      "insert into luminotes_group ( id, revision, name ) " + \
      "values ( %s, %s, %s );" % \
      ( quote( self.object_id ), quote( self.revision ), quote( self.__name ) )

  def sql_update( self ):
    return self.sql_create()

  def to_dict( self ):
    d = Persistent.to_dict( self )

    d.update( dict(
      name = self.__name,
      admin = self.__admin,
    ) )

    return d

  def __set_name( self, name ):
    self.__name = name
    self.update_revision()

  def __set_admin( self, admin ):
    # The admin member isn't actually saved to the database, so setting it doesn't need to
    # call update_revision().
    self.__admin = admin

  name = property( lambda self: self.__name, __set_name )
  admin = property( lambda self: self.__admin, __set_admin )
