import cherrypy
import types

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
      original_error = None
      try:
        result = function( *args, **kwargs )
      except cherrypy.NotFound:
        raise
      except Exception, error:
        original_error = error
        if hasattr( error, "to_dict" ):
          if not view: raise error
          result = error.to_dict()
        elif isinstance( error, cherrypy.HTTPRedirect ):
          raise
        else:
          import traceback
          traceback.print_exc()
          cherrypy.request.app.root.report_traceback()
          result = dict( error = u"An error occurred when processing your request. Please try again or contact support." )

      # if the result is a generator or a string, it's streaming data or just data, so just let CherryPy handle it
      if isinstance( result, ( types.GeneratorType, basestring ) ):
        return result

      redirect = result.get( u"redirect" )
      encoding = result.get( u"manual_encode" )
      if encoding:
        del( result[ u"manual_encode" ] )

      def render( view, result, encoding = None ):
        output = unicode( view( **result ) )
        if not encoding:
          return output
        return output.encode( encoding )

      # try using the supplied view to render the result
      try:
        if view_override is not None:
          return render( view_override, result, encoding )
        elif rss and use_rss:
          cherrypy.response.headers[ u"Content-Type" ] = u"application/xml"
          return render( rss, result, encoding or "utf8" )
        elif view:
          return render( view, result, encoding )
        elif result.get( "view" ):
          result_view = result.get( "view" )
          del( result[ "view" ] )
          return render( result_view, result, encoding )
      except:
        if redirect is None:
          if original_error:
            raise original_error
          else:
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
