import os
import os.path
import socket
import cherrypy
from tempfile import gettempdir


username_postfix = os.environ.get( "USER" )
username_postfix = username_postfix and "_%s" % username_postfix or ""


def find_available_port( port_number = 0 ):
  sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
  sock.bind( ( "", port_number ) )
  socket_port = sock.getsockname()[ 1 ]
  sock.close()
  return socket_port


# find an available TCP socket to listen on. try the default port first, and if that's not
# available, then just grab any available port that the OS gives us
DEFAULT_PORT = 6520
try:
  socket_port = find_available_port( DEFAULT_PORT )
except socket.error:
  socket_port = find_available_port()



settings = { 
  "global": {
    "server.socket_port": socket_port,
    "server.socket_host": "localhost",
    "server.thread_pool": 4,
    "session_filter.storage_class": None,
    "session_filter.storage_type": "ram",
    "session_filter.timeout": 60 * 24 * 365, # one year
    "static_filter.root": os.getcwd(),
    "server.log_to_screen": False,
    "server.log_file": os.path.join( gettempdir(), "luminotes_error%s.log" % username_postfix ),
    "server.log_access_file": os.path.join( gettempdir(), "luminotes%s.log" % username_postfix ),
    "server.log_tracebacks": True,
    "luminotes.port_file": os.path.join( gettempdir(), "luminotes_port%s" % username_postfix ),
    "luminotes.launch_browser": True,
    "luminotes.db_host": None, # use local SQLite database
    "luminotes.auto_login_username": "desktopuser",
    "luminotes.allow_shutdown_command": True, # used to stop the process during uninstall
    "luminotes.rate_plans": [
      {
        "name": "desktop",
        "designed_for": "individuals",
        "storage_quota_bytes": None, # None indicates that there is no storage quota
        "included_users": 1,
        "notebook_sharing": False,
        "notebook_collaboration": False,
        "user_admin": False,
        "fee": None,
        "yearly_fee": None,
      },
    ],
  },
  "/": {
    "tools.staticdir.root": os.path.abspath(os.getcwd()),
  },
  "/static": {
    "tools.staticdir.on": True,
    "tools.staticdir.dir": 'static' ,
  },
  "/favicon.ico": {
    "tools.staticfile.on": True,
    "tools.staticfile.filename": os.path.join( os.path.abspath(os.getcwd()),'static/images/favicon.ico') ,
  },
}
