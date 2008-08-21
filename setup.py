import sys
import py2exe
from glob import glob
from distutils.core import setup

def files( path ):
  return glob( path.replace( "/", "\\" ) )

setup(
  options = dict(
    py2exe = dict(
      packages = "cherrypy.filters",
      includes = "email.header",
    )
  ),
  console = [ "luminotes.py" ],
  data_files = [
    ( "", [ "luminotes.db", ] ),
    ( "static/css", files( "static/css/*.*" ) ),
    ( "static/html", files( "static/css/html/*.*" ) ),
    ( "static/images", files( "static/images/*.*" ) ), # TODO: exclude images like screenshots that don't need to be included
    ( "static/images/toolbar", files( "static/images/toolbar/*.*" ) ),
    ( "static/images/toolbar/small", files( "static/images/toolbar/small/*.*" ) ),
    ( "static/js", files( "static/js/*.*" ) ),
    ( "files", [] ),
  ],
)
