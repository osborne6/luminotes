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
