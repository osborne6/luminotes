from Persistent import Persistent, quote


class Download_access( Persistent ):
  """
  Access for a particular user to a downloadable product. This object is used to create unique
  per-customer product download links without requiring the user to have a Luminotes account.
  """
  def __init__( self, object_id, revision = None, item_number = None, transaction_id = None ):
    """
    Create a download access record with the given id.

    @type object_id: unicode
    @param object_id: id of the download access
    @type revision: datetime or NoneType
    @param revision: revision timestamp of the object (optional, defaults to now)
    @type item_number: unicode or NoneType
    @param item_number: number of the item to which download access is granted (optional)
    @type transaction_id: unicode or NoneType
    @param transaction_id: payment processor id for the transaction used to pay for this download
                           (optional)
    @rtype: Download_access
    @return: newly constructed download access object
    """
    Persistent.__init__( self, object_id, revision )
    self.__item_number = item_number
    self.__transaction_id = transaction_id

  @staticmethod
  def create( object_id, item_number = None, transaction_id = None ):
    """
    Convenience constructor for creating a new download access object.

    @type item_number: unicode or NoneType
    @param item_number: number of the item to which download access is granted (optional)
    @type transaction_id: unicode or NoneType
    @param transaction_id: payment processor id for the transaction used to pay for this download
                           (optional)
    @rtype: Download_access
    @return: newly constructed download access object
    """
    return Download_access( object_id, item_number = item_number, transaction_id = transaction_id )

  @staticmethod
  def sql_load( object_id, revision = None ):
    # download access objects don't store old revisions
    if revision:
      raise NotImplementedError()

    return "select id, revision, item_number, transaction_id from download_access where id = %s;" % quote( object_id )

  @staticmethod
  def sql_load_by_transaction_id( transaction_id ):
    return "select id, revision, item_number, transaction_id from download_access where transaction_id = %s;" % quote( transaction_id )

  @staticmethod
  def sql_id_exists( object_id, revision = None ):
    if revision:
      raise NotImplementedError()

    return "select id from download_access where id = %s;" % quote( object_id )

  def sql_exists( self ):
    return Download_access.sql_id_exists( self.object_id )

  def sql_create( self ):
    return "insert into download_access ( id, revision, item_number, transaction_id ) values ( %s, %s, %s, %s );" % \
    ( quote( self.object_id ), quote( self.revision ), quote( self.__item_number ), quote( self.__transaction_id ) )

  def sql_update( self ):
    return "update download_access set revision = %s, item_number = %s, transaction_id = %s where id = %s;" % \
    ( quote( self.revision ), quote( self.__item_number ), quote( self.__transaction_id ), quote( self.object_id ) )

  item_number = property( lambda self: self.__item_number )
  transaction_id = property( lambda self: self.__transaction_id )
