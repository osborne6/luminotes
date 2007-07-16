import cherrypy


def async( method ):
  """
  A decorator for a generator method that causes it to be invoked asynchronously. In other words,
  whenever a generator method decorated by this decorator is called, its generator is added to
  the scheduler for later execution.

  This decorator expects a self.scheduler member containing the scheduler to use.
  """
  def schedule( self, *args, **kwargs ):
    thread = method( self, *args, **kwargs )
    self.scheduler.add( thread )
  
  return schedule
