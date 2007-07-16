from controller.Database import Database
from controller.Scheduler import Scheduler
from model.Persistent import Persistent


class Some_object( Persistent ):
  def __init__( self, object_id, value, value2 = None, secondary_id = None ):
    Persistent.__init__( self, object_id, secondary_id )
    self.__value = value
    self.__value2 = value2

  def __set_value( self, value ):
    self.update_revision()
    self.__value = value

  def __set_value2( self, value2 ):
    self.update_revision()
    self.__value2 = value2

  value = property( lambda self: self.__value, __set_value )
  value2 = property( lambda self: self.__value2, __set_value2 )


class Test_database( object ):
  def __init__( self, clear_cache = True ):
    self.clear_cache = clear_cache

  def setUp( self ):
    self.scheduler = Scheduler()
    self.database = Database( self.scheduler )
    next_id = None

  def tearDown( self ):
    self.database.close()
    self.scheduler.shutdown()

  def test_save_and_load( self ):
    def gen():
      basic_obj = Some_object( object_id = "5", value = 1 )

      self.database.save( basic_obj, self.scheduler.thread )
      yield Scheduler.SLEEP
      if self.clear_cache: self.database.clear_cache()
      self.database.load( basic_obj.object_id, self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )

      assert obj.object_id == basic_obj.object_id
      assert obj.value == basic_obj.value

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

  def test_complex_save_and_load( self ):
    def gen():
      basic_obj = Some_object( object_id = "7", value = 2 )
      complex_obj = Some_object( object_id = "6", value = basic_obj )

      self.database.save( complex_obj, self.scheduler.thread )
      yield Scheduler.SLEEP
      if self.clear_cache: self.database.clear_cache()
      self.database.load( complex_obj.object_id, self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )
      if self.clear_cache: self.database.clear_cache()

      assert obj.object_id == complex_obj.object_id
      assert obj.value.object_id == basic_obj.object_id
      assert obj.value.value == basic_obj.value

      self.database.load( basic_obj.object_id, self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )

      assert obj.object_id == basic_obj.object_id
      assert obj.value == basic_obj.value

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

  def test_save_and_load_by_secondary( self ):
    def gen():
      basic_obj = Some_object( object_id = "5", value = 1, secondary_id = u"foo" )

      self.database.save( basic_obj, self.scheduler.thread )
      yield Scheduler.SLEEP
      if self.clear_cache: self.database.clear_cache()
      self.database.load( u"foo", self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )

      assert obj.object_id == basic_obj.object_id
      assert obj.value == basic_obj.value

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

  def test_duplicate_save_and_load( self ):
    def gen():
      basic_obj = Some_object( object_id = "9", value = 3 )
      complex_obj = Some_object( object_id = "8", value = basic_obj, value2 = basic_obj )

      self.database.save( complex_obj, self.scheduler.thread )
      yield Scheduler.SLEEP
      if self.clear_cache: self.database.clear_cache()
      self.database.load( complex_obj.object_id, self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )
      if self.clear_cache: self.database.clear_cache()

      assert obj.object_id == complex_obj.object_id
      assert obj.value.object_id == basic_obj.object_id
      assert obj.value.value == basic_obj.value
      assert obj.value2.object_id == basic_obj.object_id
      assert obj.value2.value == basic_obj.value
      assert obj.value == obj.value2

      self.database.load( basic_obj.object_id, self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )

      assert obj.object_id == basic_obj.object_id
      assert obj.value == basic_obj.value

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

  def test_save_and_load_revision( self ):
    def gen():
      basic_obj = Some_object( object_id = "5", value = 1 )
      original_revision = basic_obj.revision

      self.database.save( basic_obj, self.scheduler.thread )
      yield Scheduler.SLEEP
      if self.clear_cache: self.database.clear_cache()

      basic_obj.value = 2

      self.database.save( basic_obj, self.scheduler.thread )
      yield Scheduler.SLEEP
      if self.clear_cache: self.database.clear_cache()
      self.database.load( basic_obj.object_id, self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )
      if self.clear_cache: self.database.clear_cache()

      assert obj.object_id == basic_obj.object_id
      assert obj.revision == basic_obj.revision
      assert obj.value == basic_obj.value

      self.database.load( basic_obj.object_id, self.scheduler.thread, revision = original_revision )
      obj = ( yield Scheduler.SLEEP )

      assert obj.object_id == basic_obj.object_id
      assert obj.revision == original_revision
      assert obj.value == 1

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

  def test_load_unknown( self ):
    def gen():
      basic_obj = Some_object( object_id = "5", value = 1 )
      self.database.load( basic_obj.object_id, self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )

      assert obj == None

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

  def test_next_id( self ):
    def gen():
      self.database.next_id( self.scheduler.thread )
      next_id = ( yield Scheduler.SLEEP )
      assert next_id
      prev_ids = [ next_id ]

      self.database.next_id( self.scheduler.thread )
      next_id = ( yield Scheduler.SLEEP )
      assert next_id
      assert next_id not in prev_ids
      prev_ids.append( next_id )

      self.database.next_id( self.scheduler.thread )
      next_id = ( yield Scheduler.SLEEP )
      assert next_id
      assert next_id not in prev_ids

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )


class Test_database_without_clearing_cache( Test_database ):
  def __init__( self ):
    Test_database.__init__( self, clear_cache = False )
