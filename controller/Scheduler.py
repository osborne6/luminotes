from time import time, sleep
from threading import Thread, Semaphore


class Scheduler( object ):
  SLEEP = 0      # yielded by a generator to indicate that it should be put to sleep

  def __init__( self ):
    """
    A scheduler for generator-based microthreads.
    """
    self.__running = []  # list of active microthreads
    self.__sleeping = [] # list of sleeping microthreads
    self.__messages = {} # map of thread to list of its incoming messages
    self.__thread = None # currently executing microthread (if any)
    self.__done = False  # whether it's time to exit
    self.__idle = Semaphore( 0 )
    self.__last_error = None # used for unit tests

    self.add( self.__idle_thread() )
    self.__idle.acquire() # don't count the idle thread

    self.__scheduler_thread = Thread( target = self.run )
    self.__scheduler_thread.setDaemon( True )
    self.__scheduler_thread.start()

  def run( self ):
    """
    Run all threads repeatedly.
    """
    while not self.__done:
      self.__run_once()

  def __run_once( self ):
    """
    Run all active threads once.
    """
    turn_start = time()

    for thread in list( self.__running ):
      try:
        messages = self.__messages.get( thread )

        self.__thread = thread
        try:
          if messages:
            result = thread.send( *messages.pop( 0 ) )
          else:
            result = thread.next()
        except StopIteration:
          raise
        except Exception, e:
          self.__last_error = e
          import traceback
          traceback.print_exc()
          raise StopIteration()

        self__thread = None

        if self.__done:
          return True

        if result is None:
          continue

        # a yielded result of SLEEP indicates to put the thread to sleep
        if result == Scheduler.SLEEP:
          self.sleep( thread )
        # any other result indicates to run the yielded thread
        elif isinstance( result, ( tuple, list ) ):
          self.add( *result )
        else:
          self.add( result )
        
      except StopIteration:
        self.__idle.acquire( blocking = False )
        self.__running.remove( thread )
        self.__messages.pop( thread, None )

  def __idle_thread( self ):
    while not self.__done:
      # if the idle thread is the only one running, block until there's another running thread
      self.__idle.acquire( blocking = True )
      self.__idle.release()
      yield None

  # used for unit tests
  IDLE_SLEEP_SECONDS = 0.01
  def wait_for( self, thread ):
    while thread in self.__running or thread in self.__sleeping:
      sleep( self.IDLE_SLEEP_SECONDS )

    if self.__last_error:
      raise self.__last_error

  def wait_until_idle( self ):
    while len( self.__running ) > 1 or len( self.__sleeping ) > 0:
      sleep( self.IDLE_SLEEP_SECONDS )

  def sleep( self, thread ):
    self.__idle.acquire( blocking = False )
    self.__sleeping.append( thread )
    self.__running.remove( thread )

  def add( self, thread, *args ):
    self.__idle.release()

    if thread in self.__sleeping:
      self.__sleeping.remove( thread )
    else:
      self.__messages[ thread ] = [ ( None, ) ]

    self.__running.append( thread )

    if len( args ) > 0:
      self.__messages[ thread ].append( args )

  def shutdown( self ):
    self.__done = True
    self.__idle.release()
    self.__scheduler_thread.join()

  # currently executing microthread (if any)
  thread = property( lambda self: self.__thread )
