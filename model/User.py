import sha
import random
from copy import copy
from Persistent import Persistent, quote
from Notebook import Notebook


class User( Persistent ):
  """
  A Luminotes user.
  """
  SALT_CHARS = [ chr( c ) for c in range( ord( "!" ), ord( "~" ) + 1 ) if c != ord( "\\" ) ]
  SALT_SIZE = 12

  def __init__( self, object_id, revision = None, username = None, salt = None, password_hash = None,
                email_address = None, storage_bytes = None, rate_plan = None ):
    """
    Create a new user with the given credentials and information.

    @type object_id: unicode
    @param object_id: id of the user
    @type revision: datetime or NoneType
    @param revision: revision timestamp of the object (optional, defaults to now)
    @type username: unicode or NoneType
    @param username: unique user identifier for login purposes (optional)
    @type salt: unicode or NoneType
    @param salt: salt to use when hashing the password (optional, defaults to random)
    @type password_hash: unicode or NoneType
    @param password_hash: cryptographic hash of secret password for login purposes (optional)
    @type email_address: unicode or NoneType
    @param email_address: a hopefully valid email address (optional)
    @type storage_bytes: int or NoneType
    @param storage_bytes: count of bytes that the user is currently using for storage (optional)
    @type rate_plan: int or NoneType
    @param rate_plan: index into the rate plan array in config/Common.py (optional, defaults to 0)
    @rtype: User
    @return: newly created user
    """
    Persistent.__init__( self, object_id, revision )
    self.__username = username
    self.__salt = salt
    self.__password_hash = password_hash
    self.__email_address = email_address
    self.__storage_bytes = storage_bytes or 0
    self.__group_storage_bytes = 0
    self.__rate_plan = rate_plan or 0

  @staticmethod
  def create( object_id, username = None, password = None, email_address = None, rate_plan = None ):
    """
    Convenience constructor for creating a new user.

    @type object_id: unicode
    @param object_id: id of the user
    @type username: unicode or NoneType
    @param username: unique user identifier for login purposes (optional)
    @type password: unicode or NoneType
    @param password: secret password for login purposes (optional)
    @type email_address: unicode or NoneType
    @param email_address: a hopefully valid email address (optional)
    @type rate_plan: int or NoneType
    @param rate_plan: index into the rate plan array in config/Common.py (optional, defaults to 0)
    @rtype: User
    @return: newly created user
    """
    salt = User.__create_salt()
    password_hash = User.__hash_password( salt, password )

    return User( object_id, None, username, salt, password_hash, email_address, rate_plan = rate_plan )

  @staticmethod
  def __create_salt():
    return "".join( [ random.choice( User.SALT_CHARS ) for i in range( User.SALT_SIZE ) ] )

  @staticmethod
  def __hash_password( salt, password ):
    if password is None or len( password ) == 0:
      return None

    return sha.new( ( salt + password ).encode( "utf8" ) ).hexdigest()

  def check_password( self, password ):
    """
    Check that the given password matches this user's password.

    @type password: unicode
    @param password: password to check
    @rtype: bool
    @return: True if the password matches
    """
    if self.__password_hash == None:
      return False

    hash = User.__hash_password( self.__salt, password )
    if hash == self.__password_hash:
      return True

    return False

  @staticmethod
  def sql_load( object_id, revision = None ):
    if revision:
      return "select * from luminotes_user where id = %s and revision = %s;" % ( quote( object_id ), quote( revision ) )

    return "select * from luminotes_user_current where id = %s;" % quote( object_id )

  @staticmethod
  def sql_id_exists( object_id, revision = None ):
    if revision:
      return "select id from luminotes_user where id = %s and revision = %s;" % ( quote( object_id ), quote( revision ) )

    return "select id from luminotes_user_current where id = %s;" % quote( object_id )

  def sql_exists( self ):
    return User.sql_id_exists( self.object_id, self.revision )

  def sql_create( self ):
    return \
      "insert into luminotes_user ( id, revision, username, salt, password_hash, email_address, storage_bytes, rate_plan ) " + \
      "values ( %s, %s, %s, %s, %s, %s, %s, %s );" % \
      ( quote( self.object_id ), quote( self.revision ), quote( self.__username ),
        quote( self.__salt ), quote( self.__password_hash ), quote( self.__email_address ),
        self.__storage_bytes, self.__rate_plan )

  def sql_update( self ):
    return self.sql_create()

  @staticmethod
  def sql_load_by_username( username ):
    return "select * from luminotes_user_current where username = %s;" % quote( username )

  @staticmethod
  def sql_load_by_email_address( email_address ):
    return "select * from luminotes_user_current where email_address = %s;" % quote( email_address )

  def sql_load_notebooks( self, parents_only = False, undeleted_only = False, read_write = False,
                          tag_name = None, tag_value = None, notebook_id = None,
                          exclude_notebook_name = None, start = 0, count = None, reverse = False ):
    """
    Return a SQL string to load a list of the notebooks to which this user has access.
    """
    if parents_only:
      parents_only_clause = " and trash_id is not null"
    else:
      parents_only_clause = ""

    if undeleted_only:
      undeleted_only_clause = " and deleted = 'f'"
    else:
      undeleted_only_clause = ""

    if read_write:
      read_write_clause = " and user_notebook.read_write = 't'"
    else:
      read_write_clause = ""

    if tag_name:
      tag_tables = ", tag_notebook, tag"
      tag_clause = \
        """
         and tag_notebook.tag_id = tag.id and tag_notebook.user_id = %s and
        tag_notebook.notebook_id = notebook_current.id and tag.name = %s
        """ % ( quote( self.object_id ), quote( tag_name ) )

      if tag_value:
        tag_clause += " and tag_notebook.value = %s" % quote( tag_value )
    else:
      tag_tables = ""
      tag_clause = ""

    # useful for loading just a single notebook that the user has access to
    if notebook_id:
      notebook_id_clause = " and notebook_current.id = %s" % quote( notebook_id )
    else:
      notebook_id_clause = ""

    if exclude_notebook_name:
      notebook_name_clause = " and not notebook_current.name = %s" % quote( exclude_notebook_name )
    else:
      notebook_name_clause = ""

    if reverse:
      ordering = u"desc"
    else:
      ordering = u"asc"

    if count is not None:
      limit_clause = " limit %s" % count
    else:
      limit_clause = ""

    if start:
      offset_clause = " offset %s" % start
    else:
      offset_clause = ""

    return \
      """
      select
        notebook_current.*, user_notebook.read_write, user_notebook.owner, user_notebook.rank, user_notebook.own_notes_only,
        ( select count( note_current.id )
          from note_current
          where note_current.notebook_id = notebook_current.id and
                note_current.deleted_from_id is null )
      from
        user_notebook, notebook_current%s
      where
        user_notebook.user_id = %s%s%s%s%s%s%s and
        user_notebook.notebook_id = notebook_current.id
      order by user_notebook.rank, notebook_current.revision %s%s%s;
      """ % ( tag_tables, quote( self.object_id ), parents_only_clause, undeleted_only_clause,
              read_write_clause, tag_clause, notebook_id_clause, notebook_name_clause, ordering,
              limit_clause, offset_clause )

  def sql_count_notebooks( self, parents_only = False, undeleted_only = False, read_write = False,
                           tag_name = None, tag_value = None, exclude_notebook_name = None ):
    """
    Return a SQL string to count the number notebooks to which this user has access.
    """
    if parents_only:
      parents_only_clause = " and trash_id is not null"
    else:
      parents_only_clause = ""

    if undeleted_only:
      undeleted_only_clause = " and deleted = 'f'"
    else:
      undeleted_only_clause = ""

    if read_write:
      read_write_clause = " and user_notebook.read_write = 't'"
    else:
      read_write_clause = ""

    if tag_name:
      tag_tables = ", tag_notebook, tag"
      tag_clause = \
        """
         and tag_notebook.tag_id = tag.id and tag_notebook.user_id = %s and
        tag_notebook.notebook_id = notebook_current.id and tag.name = %s
        """ % ( quote( self.object_id ), quote( tag_name ) )

      if tag_value:
        tag_clause += " and tag_notebook.value = %s" % quote( tag_value )
    else:
      tag_tables = ""
      tag_clause = ""

    if exclude_notebook_name:
      notebook_name_clause = " and not notebook_current.name = %s" % quote( exclude_notebook_name )
    else:
      notebook_name_clause = ""

    return \
      """
      select
        count( notebook_current.id )
      from
        user_notebook, notebook_current%s
      where
        user_notebook.user_id = %s%s%s%s%s%s and
        user_notebook.notebook_id = notebook_current.id;
      """ % ( tag_tables, quote( self.object_id ), parents_only_clause, undeleted_only_clause,
              read_write_clause, tag_clause, notebook_name_clause )

  def sql_save_notebook( self, notebook_id, read_write = True, owner = True, rank = None, own_notes_only = False ):
    """
    Return a SQL string to save the id of a notebook to which this user has access.
    """
    if rank is None: rank = quote( None )

    return \
      "insert into user_notebook ( user_id, notebook_id, read_write, owner, rank, own_notes_only ) values " + \
      "( %s, %s, %s, %s, %s, %s );" % (
        quote( self.object_id ),
        quote( notebook_id ),
        quote( read_write and 't' or 'f' ),
        quote( owner and 't' or 'f' ),
        rank,
        quote( own_notes_only and 't' or 'f' ),
      )

  def sql_remove_notebook( self, notebook_id ):
    """
    Return a SQL string to remove this user's access to a particular notebook.
    """
    return \
      "delete from user_notebook where user_id = %s and notebook_id = %s;" % ( quote( self.object_id ), quote( notebook_id ) )

  def sql_has_access( self, notebook_id, read_write = False, owner = False ):
    """
    Return a SQL string to determine whether this user has access to the given notebook.
    """
    if read_write is True and owner is True:
      return \
        "select user_id from user_notebook where user_id = %s and notebook_id = %s and read_write = 't' and owner = 't';" % \
        ( quote( self.object_id ), quote( notebook_id ) )
    elif read_write is True:
      return \
        "select user_id from user_notebook where user_id = %s and notebook_id = %s and read_write = 't';" % \
        ( quote( self.object_id ), quote( notebook_id ) )
    elif owner is True:
      return \
        "select user_id from user_notebook where user_id = %s and notebook_id = %s and owner = 't';" % \
        ( quote( self.object_id ), quote( notebook_id ) )
    else:
      return \
        "select user_id from user_notebook where user_id = %s and notebook_id = %s;" % \
        ( quote( self.object_id ), quote( notebook_id ) )

  def sql_update_access( self, notebook_id, read_write = Notebook.READ_ONLY, owner = False ):
    """
    Return a SQL string to update the user's notebook access to the given read_write and owner level.
    """
    return \
      "update user_notebook set read_write = %s, owner = %s, own_notes_only = %s where user_id = %s and notebook_id = %s;" % (
        quote( ( read_write not in ( Notebook.READ_ONLY, False ) ) and 't' or 'f' ),
        quote( owner and 't' or 'f' ),
        quote( ( read_write == Notebook.READ_WRITE_FOR_OWN_NOTES ) and 't' or 'f' ),
        quote( self.object_id ),
        quote( notebook_id ),
      )

  def sql_save_notebook_tag( self, notebook_id, tag_id, value = None ):
    """
    Return a SQL string to associate a tag with a notebook of this user.
    """
    return \
      "insert into tag_notebook ( notebook_id, tag_id, value, user_id ) values " + \
      "( %s, %s, %s, %s );" % ( quote( notebook_id ), quote( tag_id ), quote( value ), quote( self.object_id ) )

  def sql_update_notebook_rank( self, notebook_id, rank ):
    """
    Return a SQL string to update the user's rank for the given notebook.
    """
    return \
      "update user_notebook set rank = %s where user_id = %s and notebook_id = %s;" % \
      ( quote( rank ), quote( self.object_id ), quote( notebook_id ) )

  def sql_highest_notebook_rank( self ):
    """
    Return a SQL string to determine the highest numbered rank of all notebooks the user has access to."
    """
    return "select coalesce( max( rank ), -1 ) from user_notebook where user_id = %s;" % quote( self.object_id )

  def sql_load_groups( self ):
    """
    Return a SQL string to load a list of the groups to which this user has membership.
    """
    return \
      """
      select
        luminotes_group_current.*, user_group.admin
      from
        user_group, luminotes_group_current
      where
        user_group.user_id = %s and
        user_group.group_id = luminotes_group_current.id
      order by luminotes_group_current.name;
      """ % quote( self.object_id )

  def sql_save_group( self, group_id, admin = False ):
    """
    Return a SQL string to save the id of a group to which this user has membership.
    """
    return \
      "insert into user_group ( user_id, group_id, admin ) values " + \
      "( %s, %s, %s );" % ( quote( self.object_id ), quote( group_id ), quote( admin and 't' or 'f' ) )

  def sql_remove_group( self, group_id ):
    """
    Return a SQL string to remove this user's membership to a particular group.
    """
    return \
      "delete from user_group where user_id = %s and group_id = %s;" % ( quote( self.object_id ), quote( group_id ) )

  def sql_in_group( self, group_id, admin = False ):
    """
    Return a SQL string to determine whether this has membership to the given group.
    """
    if admin is True:
      return \
        "select user_id from user_group where user_id = %s and group_id = %s and admin = 't';" % \
        ( quote( self.object_id ), quote( group_id ) )
    else:
      return \
        "select user_id from user_group where user_id = %s and group_id = %s;" % \
        ( quote( self.object_id ), quote( group_id ) )

  def sql_update_group_admin( self, group_id, admin = False ):
    """
    Return a SQL string to update the user's group membership to have the given admin flag.
    """
    return \
      "update user_group set admin = %s where user_id = %s and group_id = %s;" % \
      ( quote( admin and 't' or 'f' ), quote( self.object_id ), quote( group_id ) )

  @staticmethod
  def sql_revoke_invite_access( notebook_id, trash_id, email_address ):
    return \
      """
      delete from
        user_notebook
      where
        notebook_id in ( %s, %s ) and
        user_notebook.user_id in (
          select
            redeemed_user_id
          from
            invite
          where
            notebook_id = %s and
            email_address = %s
        );
      """ % ( quote( notebook_id ), quote( trash_id ), quote( notebook_id ), quote( email_address ) )

  def sql_calculate_storage( self, database_backend ):
    """
    Return a SQL string to calculate the total bytes of storage usage by this user. This includes
    storage for all the user's notes (including past revisions) and their uploaded files. It does
    not include storage for the notebooks themselves.
    """
    if database_backend == Persistent.POSTGRESQL_BACKEND:
      # this counts bytes for the contents of each column
      note_size_clause = "pg_column_size( note.* )"
    else:
      # this isn't perfect, because length() counts UTF-8 characters instead of bytes.
      # some columns are left out because they can be null, which screws up the addition
      note_size_clause = \
        """
        length( note.id ) + length( note.revision ) + length( note.title ) + length( note.contents ) +
        length( note.notebook_id ) + length( note.startup ) + length( note.user_id )
        """

    return \
      """
      select * from (
        select
          coalesce( sum( %s ), 0 )
        from
          user_notebook, note
        where
          user_notebook.user_id = %s and
          user_notebook.owner = 't' and
          note.notebook_id = user_notebook.notebook_id
      ) as note_storage,
      (
        select
          coalesce( sum( file.size_bytes ), 0 )
        from
          user_notebook, file
        where
          user_notebook.user_id = %s and
          user_notebook.owner = 't' and
          file.notebook_id = user_notebook.notebook_id
      ) as file_storage;
      """ % ( note_size_clause, quote( self.object_id ), quote( self.object_id ) )

  def sql_calculate_group_storage( self ):
    """
    Return a SQL string to calculate the total bytes of storage usage for all groups that this user
    is a member of. This includes the cumulative storage of all users in these groups.
    """
    return \
      """
      select coalesce( sum( storage_bytes ), 0 ) from (
        select
          distinct user_id, storage_bytes
        from
          user_group, luminotes_user_current
        where
          group_id in (
            select
              group_id
            from
              user_group
            where
              user_id = %s
            ) and
          user_id = luminotes_user_current.id
      ) as sub;
      """ % quote( self.object_id )

  def to_dict( self ):
    d = Persistent.to_dict( self )
    d.update( dict(
      username = self.username,
      email_address = self.__email_address,
      storage_bytes = self.__storage_bytes,
      group_storage_bytes = self.__group_storage_bytes,
      rate_plan = self.__rate_plan,
    ) )

    return d

  def __set_email_address( self, email_address ):
    self.update_revision()
    self.__email_address = email_address

  def __set_password( self, password ):
    self.update_revision()
    self.__salt = User.__create_salt()
    self.__password_hash = User.__hash_password( self.__salt, password )

  def __set_storage_bytes( self, storage_bytes ):
    self.update_revision()
    self.__storage_bytes = storage_bytes

  def __set_group_storage_bytes( self, group_storage_bytes ):
    # The group_storage_bytes member isn't actually saved to the database, so setting it doesn't
    # need to call update_revision().
    self.__group_storage_bytes = group_storage_bytes

  def __set_rate_plan( self, rate_plan ):
    self.update_revision()
    self.__rate_plan = rate_plan

  username = property( lambda self: self.__username )
  email_address = property( lambda self: self.__email_address, __set_email_address )
  password = property( None, __set_password )
  storage_bytes = property( lambda self: self.__group_storage_bytes or self.__storage_bytes, __set_storage_bytes )
  group_storage_bytes = property( lambda self: self.__group_storage_bytes, __set_group_storage_bytes )
  rate_plan = property( lambda self: self.__rate_plan, __set_rate_plan )
