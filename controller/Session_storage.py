import cherrypy
from cherrypy.filters.sessionfilter import PostgreSQLStorage


class Session_storage( PostgreSQLStorage ):
  """
  A wrapper for CherryPy's PostgreSQLStorage class that commits the current transaction to the
  database so session changes actually take effect.
  """

  def __init__( self ):
    self.db = cherrypy.root.database.get_connection()
    self.cursor = self.db.cursor()

  def save( self, *args, **kwargs ):
    PostgreSQLStorage.save( self, *args, **kwargs )
    self.db.commit()

  def clean_up( self, *args, **kwargs ):
    PostgreSQLStorage.clean_up( self, *args, **kwargs )
    self.db.commit()
