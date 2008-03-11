import os
import cherrypy


settings = { 
  "global": {
    "server.thread_pool": 10,
    "autoreload.on": True,
    "static_filter.root": os.getcwd(),
  },
  "/static": {
    "static_filter.on": True,
    "static_filter.dir": "static",
  },
  "/favicon.ico": {
    "static_filter.on": True,
    "static_filter.file": "static/images/favicon.ico",
  },
}
