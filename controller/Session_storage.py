import cherrypy
from  psycopg2 import ProgrammingError
from cherrypy.filters.sessionfilter import PostgreSQLStorage


class Session_storage( PostgreSQLStorage ):
  """
  A wrapper for CherryPy's PostgreSQLStorage class that commits the current transaction to the
  database so session changes actually take effect.
  """

  def __init__( self ):
    self.db = cherrypy.root.database.get_connection()
    self.cursor = self.db.cursor()

  def load( self, *args, **kwargs ):
    try:
      return PostgreSQLStorage.load( self, *args, **kwargs )
    # catch "ProgrammingError: no results to fetch" from self.cursor.fetchall()
    except ProgrammingError:
      return None

  def save( self, *args, **kwargs ):
    PostgreSQLStorage.save( self, *args, **kwargs )
    self.db.commit()

  def clean_up( self, *args, **kwargs ):
    PostgreSQLStorage.clean_up( self, *args, **kwargs )
    self.db.commit()
