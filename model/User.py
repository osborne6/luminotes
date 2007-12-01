import sha
import random
from copy import copy
from Persistent import Persistent, quote


class User( Persistent ):
  """
  A Luminotes user.
  """
  SALT_CHARS = [ chr( c ) for c in range( ord( "!" ), ord( "~" ) + 1 ) ]
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
    self.__rate_plan = rate_plan or 0

  @staticmethod
  def create( object_id, username = None, password = None, email_address = None ):
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
    @rtype: User
    @return: newly created user
    """
    salt = User.__create_salt()
    password_hash = User.__hash_password( salt, password )

    return User( object_id, None, username, salt, password_hash, email_address )

  @staticmethod
  def __create_salt():
    return "".join( [ random.choice( User.SALT_CHARS ) for i in range( User.SALT_SIZE ) ] )

  @staticmethod
  def __hash_password( salt, password ):
    if password is None or len( password ) == 0:
      return None

    return sha.new( salt + password ).hexdigest()

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

  def sql_load_notebooks( self, parents_only = False, undeleted_only = False ):
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

    return \
      "select notebook_current.*, user_notebook.read_write from user_notebook, notebook_current " + \
      "where user_notebook.user_id = %s%s%s and user_notebook.notebook_id = notebook_current.id order by revision;" % \
      ( quote( self.object_id ), parents_only_clause, undeleted_only_clause )

  def sql_save_notebook( self, notebook_id, read_write = True ):
    """
    Return a SQL string to save the id of a notebook to which this user has access.
    """
    return \
      "insert into user_notebook ( user_id, notebook_id, read_write ) values " + \
      "( %s, %s, %s );" % ( quote( self.object_id ), quote( notebook_id ), quote( read_write and 't' or 'f' ) )

  def sql_remove_notebook( self, notebook_id ):
    """
    Return a SQL string to remove this user's access to a particular notebook.
    """
    return \
      "delete from user_notebook where user_id = %s and notebook_id = %s;" % ( quote( self.object_id ), quote( notebook_id ) )

  def sql_has_access( self, notebook_id, read_write = False ):
    """
    Return a SQL string to determine whether this user has access to the given notebook.
    """
    if read_write is True:
      return \
        "select user_id from user_notebook where user_id = %s and notebook_id = %s and read_write = 't';" % \
        ( quote( self.object_id ), quote( notebook_id ) )
    else:
      return \
        "select user_id from user_notebook where user_id = %s and notebook_id = %s;" % \
        ( quote( self.object_id ), quote( notebook_id ) )

  def sql_calculate_storage( self ):
    """
    Return a SQL string to calculate the total bytes of storage usage by this user. Note that this
    only includes storage for all the user's notes and past revisions. It doesn't include storage
    for the notebooks themselves.
    """
    return \
      """
      select
        coalesce( sum( pg_column_size( note.* ) ), 0 )
      from
        user_notebook, note
      where
        user_notebook.user_id = %s and
        note.notebook_id = user_notebook.notebook_id;
      """ % quote( self.object_id )

  def to_dict( self ):
    d = Persistent.to_dict( self )
    d.update( dict(
      username = self.username,
      storage_bytes = self.__storage_bytes,
      rate_plan = self.__rate_plan,
    ) )

    return d

  def __set_password( self, password ):
    self.update_revision()
    self.__salt = User.__create_salt()
    self.__password_hash = User.__hash_password( self.__salt, password )

  def __set_storage_bytes( self, storage_bytes ):
    self.update_revision()
    self.__storage_bytes = storage_bytes

  def __set_rate_plan( self, rate_plan ):
    self.update_revision()
    self.__rate_plan = rate_plan

  username = property( lambda self: self.__username )
  email_address = property( lambda self: self.__email_address )
  password = property( None, __set_password )
  storage_bytes = property( lambda self: self.__storage_bytes, __set_storage_bytes )
  rate_plan = property( lambda self: self.__rate_plan, __set_rate_plan )
