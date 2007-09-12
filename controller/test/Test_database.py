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
      original_revision = basic_obj.revision

      self.database.save( basic_obj, self.scheduler.thread )
      yield Scheduler.SLEEP
      if self.clear_cache: self.database.clear_cache()
      self.database.load( basic_obj.object_id, self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )

      assert obj.object_id == basic_obj.object_id
      assert obj.revision == original_revision
      assert obj.revisions_list == [ original_revision ]
      assert obj.value == basic_obj.value

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

  def test_complex_save_and_load( self ):
    def gen():
      basic_obj = Some_object( object_id = "7", value = 2 )
      basic_original_revision = basic_obj.revision
      complex_obj = Some_object( object_id = "6", value = basic_obj )
      complex_original_revision = complex_obj.revision

      self.database.save( complex_obj, self.scheduler.thread )
      yield Scheduler.SLEEP
      if self.clear_cache: self.database.clear_cache()
      self.database.load( complex_obj.object_id, self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )
      if self.clear_cache: self.database.clear_cache()

      assert obj.object_id == complex_obj.object_id
      assert obj.revision == complex_original_revision
      assert obj.revisions_list == [ complex_original_revision ]
      assert obj.value.object_id == basic_obj.object_id
      assert obj.value.value == basic_obj.value
      assert obj.value.revision == basic_original_revision
      assert obj.value.revisions_list == [ basic_original_revision ]

      self.database.load( basic_obj.object_id, self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )

      assert obj.object_id == basic_obj.object_id
      assert obj.value == basic_obj.value
      assert obj.revision == basic_original_revision
      assert obj.revisions_list == [ basic_original_revision ]

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

  def test_save_and_load_by_secondary( self ):
    def gen():
      basic_obj = Some_object( object_id = "5", value = 1, secondary_id = u"foo" )
      original_revision = basic_obj.revision

      self.database.save( basic_obj, self.scheduler.thread )
      yield Scheduler.SLEEP
      if self.clear_cache: self.database.clear_cache()
      self.database.load( u"Some_object foo", self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )

      assert obj.object_id == basic_obj.object_id
      assert obj.value == basic_obj.value
      assert obj.revision == original_revision
      assert obj.revisions_list == [ original_revision ]

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

  def test_duplicate_save_and_load( self ):
    def gen():
      basic_obj = Some_object( object_id = "9", value = 3 )
      basic_original_revision = basic_obj.revision
      complex_obj = Some_object( object_id = "8", value = basic_obj, value2 = basic_obj )
      complex_original_revision = complex_obj.revision

      self.database.save( complex_obj, self.scheduler.thread )
      yield Scheduler.SLEEP
      if self.clear_cache: self.database.clear_cache()
      self.database.load( complex_obj.object_id, self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )
      if self.clear_cache: self.database.clear_cache()

      assert obj.object_id == complex_obj.object_id
      assert obj.revision == complex_original_revision
      assert obj.revisions_list == [ complex_original_revision ]

      assert obj.value.object_id == basic_obj.object_id
      assert obj.value.value == basic_obj.value
      assert obj.value.revision == basic_original_revision
      assert obj.value.revisions_list == [ basic_original_revision ]

      assert obj.value2.object_id == basic_obj.object_id
      assert obj.value2.value == basic_obj.value
      assert obj.value2.revision == basic_original_revision
      assert obj.value2.revisions_list == [ basic_original_revision ]

      assert obj.value == obj.value2

      self.database.load( basic_obj.object_id, self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )

      assert obj.object_id == basic_obj.object_id
      assert obj.value == basic_obj.value
      assert obj.revision == basic_original_revision
      assert obj.revisions_list == [ basic_original_revision ]

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
      assert obj.revisions_list == [ original_revision, basic_obj.revision ]
      assert obj.value == basic_obj.value

      self.database.load( basic_obj.object_id, self.scheduler.thread, revision = original_revision )
      revised = ( yield Scheduler.SLEEP )

      assert revised.object_id == basic_obj.object_id
      assert revised.value == 1
      assert revised.revision == original_revision
      assert id( obj.revisions_list ) != id( revised.revisions_list )
      assert revised.revisions_list == [ original_revision ]

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

  def test_reload( self ):
    def gen():
      basic_obj = Some_object( object_id = "5", value = 1 )
      original_revision = basic_obj.revision

      self.database.save( basic_obj, self.scheduler.thread )
      yield Scheduler.SLEEP
      if self.clear_cache: self.database.clear_cache()

      def setstate( self, state ):
        state[ "_Some_object__value" ] = 55
        self.__dict__.update( state )

      Some_object.__setstate__ = setstate

      self.database.reload( basic_obj.object_id, self.scheduler.thread )
      yield Scheduler.SLEEP
      delattr( Some_object, "__setstate__" )
      if self.clear_cache: self.database.clear_cache()

      self.database.load( basic_obj.object_id, self.scheduler.thread )
      obj = ( yield Scheduler.SLEEP )

      assert obj.object_id == basic_obj.object_id
      assert obj.value == 55
      assert obj.revision == original_revision
      assert obj.revisions_list == [ original_revision ]

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

  def test_reload_revision( self ):
    def gen():
      basic_obj = Some_object( object_id = "5", value = 1 )
      original_revision = basic_obj.revision
      original_revision_id = basic_obj.revision_id()

      self.database.save( basic_obj, self.scheduler.thread )
      yield Scheduler.SLEEP
      if self.clear_cache: self.database.clear_cache()

      basic_obj.value = 2

      self.database.save( basic_obj, self.scheduler.thread )
      yield Scheduler.SLEEP
      if self.clear_cache: self.database.clear_cache()

      def setstate( self, state ):
        state[ "_Some_object__value" ] = 55
        self.__dict__.update( state )

      Some_object.__setstate__ = setstate

      self.database.reload( original_revision_id, self.scheduler.thread )
      yield Scheduler.SLEEP
      delattr( Some_object, "__setstate__" )
      if self.clear_cache: self.database.clear_cache()

      self.database.load( basic_obj.object_id, self.scheduler.thread, revision = original_revision )
      obj = ( yield Scheduler.SLEEP )

      assert obj.object_id == basic_obj.object_id
      assert obj.revision == original_revision
      assert obj.revisions_list == [ original_revision ]
      assert obj.value == 55

    g = gen()
    self.scheduler.add( g )
    self.scheduler.wait_for( g )

  def test_size( self ):
    def gen():
      basic_obj = Some_object( object_id = "5", value = 1 )
      original_revision = basic_obj.revision

      self.database.save( basic_obj, self.scheduler.thread )
      yield Scheduler.SLEEP
      if self.clear_cache: self.database.clear_cache()

      size = self.database.size( basic_obj.object_id )

      from cPickle import Pickler
      from StringIO import StringIO
      buffer = StringIO()
      pickler = Pickler( buffer, protocol = -1 )
      pickler.dump( basic_obj )
      expected_size = len( buffer.getvalue() )

      # as long as the size is close to the expected size, that's fine
      assert abs( size - expected_size ) < 10

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
