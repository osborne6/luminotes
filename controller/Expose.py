import cherrypy

# module-level variable that, when set to a view, overrides the view for all exposed methods. used
# by unit tests
view_override = None


def expose( view = None, rss = None ):
  """
  expose() can be used to tag a method as available for publishing to the web via CherryPy. In
  other words, methods that are not exposed cannot be accessed from the web.

  The expose() method itself is evaluated where it is used as a decorator, which just puts the view
  variable into the enclosing scope of the decorate() function and returns decorate() to be used as
  the actual decorator.

  Example usage:

    @expose( view = Json )
    def method(): pass
  """
  def decorate( function ):
    """
    When the method being decorated is invoked, its decorator gets invoked instead and is supposed
    to return a new function to use in place of the method being decorated (or a modified version
    of that function). In this case, the decorator is our decorate() function, and the function it
    returns is the render() function. decorate()'s first argument is the method being decorated.
    """
    def render( *args, **kwargs ):
      """
      render() pretends that it's the method being decorated. It takes the same arguments and then
      invokes the actual method being decorated, passing in those arguments.

      With whatever result it gets from calling that method, render() invokes the view from the
      outer scope to try to render it. It then results that rendered result.
      """
      result = {}

      # if rss was requested, and this method was exposed for rss, then use rss as the view
      if u"rss" in kwargs:
        del kwargs[ u"rss" ]
        use_rss = True
      else:
        use_rss = False

      # kwarg names must be of type str, not unicode
      kwargs = dict( [ ( str( key ), value ) for ( key, value ) in kwargs.items() ] )

      # try executing the exposed function
      try:
        result = function( *args, **kwargs )
      except cherrypy.NotFound:
        raise
      except Exception, error:
        if hasattr( error, "to_dict" ):
          result = error.to_dict()
        else:
          import traceback
          traceback.print_exc()
          cherrypy.root.report_traceback()
          result = dict( error = u"An error occurred when processing your request. Please try again or contact support." )

      redirect = result.get( u"redirect", None )

      # try using the supplied view to render the result
      try:
        if view_override is None:
          if rss and use_rss:
            cherrypy.response.headers[ u"Content-Type" ] = u"application/xml"
            return unicode( rss( **result ) )
          elif view:
            return unicode( view( **result ) )
        else:
          return unicode( view_override( **result ) )
      except:
        if redirect is None:
          print result
          raise

      # if that doesn't work, and there's a redirect, then redirect
      del( result[ u"redirect" ] )
      from urllib import urlencode

      if result == {}:
        raise cherrypy.HTTPRedirect( u"%s" % redirect )
      else:
        url_args = urlencode( result )
        raise cherrypy.HTTPRedirect( u"%s?%s" % ( redirect, url_args ) )

    render.exposed = True
    return render

  return decorate
