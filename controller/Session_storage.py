import cherrypy
import cPickle as pickle
from datetime import datetime
from psycopg2 import ProgrammingError


class Session_storage( object ):
  """
  A CherryPy session storage class, originally based on CherryPy's PostgreSQLStorage. It assumes
  a table like this:

    create table session (
      id text,
      data text,
      expiration_time timestamp
    )

  It differs from PostgreSQLStorage in the following ways:

    * changes to the database are actually committed after they are made
    * a new cursor is created for each database access to prevent problems with multiple threads
    * a connection is requested from cherrypy.root.database instead of a session_filter.get_db method
    * __del__ is not implemented because it should not be relied upon
    * no locking is implemented
  """
  def __init__( self ):
    self.conn = cherrypy.root.database.get_connection()
  
  def load( self, id ):
    cursor = self.conn.cursor()

    # Select session data from table
    cursor.execute(
      'select data, expiration_time from session where id=%s',
      (id,))
    rows = cursor.fetchall()
    if not rows:
      return None
    pickled_data, expiration_time = rows[0]
    # Unpickle data
    data = pickle.loads(pickled_data)
    return (data, expiration_time)
  
  def save( self, id, data, expiration_time ):
    cursor = self.conn.cursor()

    # Try to delete session if it was already there
    cursor.execute(
      'delete from session where id=%s',
      (id,))
    # Pickle data
    pickled_data = pickle.dumps(data)
    # Insert new session data
    cursor.execute(
      'insert into session (id, data, expiration_time) values (%s, %s, %s)',
      (id, pickled_data, expiration_time))

    self.conn.commit()
  
  def clean_up( self, sess ):
    cursor = self.conn.cursor()

    now = datetime.now()
    cursor.execute(
      'select data from session where expiration_time < %s',
      (now,))
    rows = cursor.fetchall()
    for row in rows:
      sess.on_delete_session(row[0])
    cursor.execute(
      'delete from session where expiration_time < %s',
      (now,))

    self.conn.commit()

  def acquire_lock( self ):
    raise NotImplemented()
  
  def release_lock( self ):
    raise NotImplemented()
