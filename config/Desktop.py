import os
import cherrypy


settings = { 
  "global": {
    "server.thread_pool": 4,
    "session_filter.storage_type": "ram",
    "session_filter.timeout": 60 * 24 * 365, # one year
    "static_filter.root": os.getcwd(),
    "server.log_to_screen": True,
    "luminotes.launch_browser": True,
    "luminotes.db_host": None, # use local SQLite database
    "luminotes.auto_login_username": "desktopuser",
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
  "/static": {
    "static_filter.on": True,
    "static_filter.dir": "static",
    "session_filter.on": False,
  },
  "/favicon.ico": {
    "static_filter.on": True,
    "static_filter.file": "static/images/favicon.ico",
    "session_filter.on": False,
  },
}