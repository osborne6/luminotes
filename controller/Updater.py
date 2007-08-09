from Queue import Queue, Empty


TIMEOUT_SECONDS = 10.0


def wait_for_update( function ):
  """
  A decorator that passes a "queue" keyword arugment to its decorated function, calls the function,
  and then blocks until an asynchronous response comes back via the Queue. When a response is
  received, wait_for_update() returns it.

  For this decorator to be useful, you should use it to decorate a function that fires off some
  asynchronous action and then returns immediately. A typical way to accomplish this is by using
  the @async decorator after the @wait_for_update decorator.
  """
  def get_message( *args, **kwargs ):
    queue = Queue()

    kwargs[ "queue" ] = queue
    function( *args, **kwargs )

    # wait until a response is available in the queue, and then return that response
    try:
      return queue.get( block = True, timeout = TIMEOUT_SECONDS )
    except Empty:
      return { "error": u"A timeout occurred when processing your request. Please try again or contact support@luminotes.com" }

  return get_message


def update_client( function ):
  """
  A decorator used to wrap a generator function so that its yielded values can be issued as
  updates to the client. For this to work, the generator function must be invoked with a keyword
  argument "queue" containing a Queue where the result can be put().

  Also supports catching Validation_error exceptions and sending appropriate errors to the client.

  Note that this decorator itself is a generator function and works by passing along next()/send()
  calls to its decorated generator. Only yielded values that are dictionaries are sent to the
  client via the provided queue. All other types of yielded values are in turn yielded by this
  decorator itself.
  """
  def put_message( *args, **kwargs ):
    # look in the called function's kwargs for the queue where results should be sent
    queue = kwargs.pop( "queue" )

    try:
      generator = function( *args, **kwargs )
      message = None

      while True:
        result = generator.send( message )

        if isinstance( result, dict ):
          queue.put( result )
          message = ( yield None )
        else:
          message = ( yield result )
    except StopIteration:
      return
    except Exception, error:
      # TODO: might be better to use view.Json instead of calling to_dict() manually
      if hasattr( error, "to_dict" ):
        result = error.to_dict()
        queue.put( result )
      else:
        queue.put( { "error": u"An error occurred when processing your request. Please try again or contact support@luminotes.com" } )
        raise
  
  return put_message
