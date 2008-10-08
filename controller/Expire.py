import cherrypy


def strongly_expire( function ):
  """
  Decorator that sends headers that instruct browsers and proxies not to cache.
  """
  def expire( *args, **kwargs ):
    cherrypy.response.headers[ "Expires" ] = "Sun, 19 Nov 1978 05:00:00 GMT"
    cherrypy.response.headers[ "Cache-Control" ] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0"
    cherrypy.response.headers[ "Pragma" ] = "no-cache"

    return function( *args, **kwargs )

  return expire


def weakly_expire( function ):
  """
  Decorator that sends headers that instruct browsers and proxies not to cache. This cache busting
  isn't as strong as the @strongly_expire decorator, but it has the distinct benefit of not
  breaking Internet Explorer HTTPS file downloads.
  """
  def expire( *args, **kwargs ):
    cherrypy.response.headers[ "Expires" ] = "Sun, 19 Nov 1978 05:00:00 GMT"

    return function( *args, **kwargs )

  return expire
