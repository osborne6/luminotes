import cherrypy


MEGABYTE = 1024 * 1024


settings = { 
  "global": {
    "server.socket_port": 8081,
    "server.environment": "production",
    "session_filter.on": True,
    "session_filter.storage_type": "file",
    "session_filter.storage_path": "session",
    "session_filter.timeout": 60 * 72, # 72 hours
    "session_filter.clean_up_delay": 5,
    "session_filter.locking": "implicit",
    "encoding_filter.on": True,
    "encoding_filter.encoding": "utf-8",
    "decoding_filter.on": True,
    "decoding_filter.encoding": "utf-8",
    "luminotes.http_url": "",
    "luminotes.https_url": "",
    "luminotes.http_proxy_ip": "127.0.0.1",
    "luminotes.https_proxy_ip": "127.0.0.2",
    "luminotes.support_email": "",
    "luminotes.rate_plans": [
      {
        "name": "free",
        "storage_quota_bytes": 30 * MEGABYTE,
        "notebook_collaboration": False,
        "fee": None,
      },
      {
        "name": "basic",
        "storage_quota_bytes": 250 * MEGABYTE,
        "notebook_collaboration": True,
        "fee": 5,
        "button":
          """
          """,
      },
      {
        "name": "standard",
        "storage_quota_bytes": 500 * MEGABYTE,
        "notebook_collaboration": True,
        "fee": 9,
        "button":
          """
          """,
      },
#      {
#        "name": "premium",
#        "storage_quota_bytes": 2000 * MEGABYTE,
#        "notebook_collaboration": True,
#        "fee": 19,
#      },
    ],
    "luminotes.unsubscribe_button":
      """
      """,
  },
}
