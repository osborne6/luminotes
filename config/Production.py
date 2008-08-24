import cherrypy


settings = { 
  "global": {
    "server.socket_queue_size": 15,
    "server.thread_pool": 40,
    "base_url_filter.on": True,
    "base_url_filter.use_x_forwarded_host": True,
    "server.log_to_screen": False,
    "server.log_file": "luminotes_error.log",
    "server.log_access_file": "luminotes.log",
    "server.log_tracebacks": True,
  },
}
