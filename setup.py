import sys
#import py2exe
from glob import glob
from distutils.core import setup, Distribution


def files( path ):
  if sys.platform.startswith( "win" ):
    path = path.replace( "/", "\\" )

  return glob( path )


class Luminotes( Distribution ):
  def __init__( self, attrs ):
    self.console = [ "luminotes.py" ]
    Distribution.__init__( self, attrs )


setup(
  distclass = Luminotes,
  data_files = [
    ( "", [ "luminotes.db", ] ),
    ( "static/css", files( "static/css/*.*" ) ),
    ( "static/html", files( "static/css/html/*.*" ) ),
    ( "static/images", files( "static/images/*.*" ) ),
    ( "static/images/toolbar", files( "static/images/toolbar/*.*" ) ),
    ( "static/images/toolbar/small", files( "static/images/toolbar/small/*.*" ) ),
    ( "static/js", files( "static/js/*.*" ) ),
    ( "files", [] ),
  ],
  options = dict(
    py2exe = dict(
      packages = "cherrypy.filters",
      includes = "email.header",
    )
  ),
)
