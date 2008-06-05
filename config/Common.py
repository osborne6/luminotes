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
    "luminotes.db_host": "localhost",
    "luminotes.db_ssl_mode": "allow", # "disallow", "allow", "prefer", or "require"
    "luminotes.support_email": "",
    "luminotes.payment_email": "",
    "luminotes.rate_plans": [
      {
        "name": "free",
        "designed_for": "students",
        "storage_quota_bytes": 30 * MEGABYTE,
        "included_users": 1,
        "notebook_collaboration": False,
        "user_admin": False,
        "fee": None,
        "yearly_fee": None,
      },
      {
        "name": "basic",
        "designed_for": "home users",
        "storage_quota_bytes": 250 * MEGABYTE,
        "included_users": 1,
        "notebook_collaboration": True,
        "user_admin": False,
        "fee": 5,
        "yearly_fee": 50,
        "button":
          """
          """,
        "yearly_button":
          """
          """,
      },
      {
        "name": "standard",
        "designed_for": "professionals",
        "storage_quota_bytes": 500 * MEGABYTE,
        "included_users": 1,
        "notebook_collaboration": True,
        "user_admin": False,
        "fee": 9,
        "yearly_fee": 90,
        "button":
          """
          """,
        "yearly_button":
          """
          """,
      },
      {
        "name": "plus",
        "designed_for": "small teams",
        "storage_quota_bytes": 1000 * MEGABYTE,
        "included_users": 5,
        "notebook_collaboration": True,
        "user_admin": True,
        "fee": 19,
        "yearly_fee": 190,
        "button":
          """
          """,
        "yearly_button":
          """
          """,
      },
      {
        "name": "premium",
        "designed_for": "organizations",
        "storage_quota_bytes": 5000 * MEGABYTE,
        "included_users": 30,
        "notebook_collaboration": True,
        "user_admin": True,
        "fee": 99,
        "yearly_fee": 990,
        "button":
          """
          """,
        "yearly_button":
          """
          """,
      },
    ],
    "luminotes.unsubscribe_button":
      """
      """,
  },
  "/files/download": {
    "stream_response": True,
    "encoding_filter.on": False,
  },
  "/files/upload": {
    "server.max_request_body_size": 505 * MEGABYTE, # maximum upload size
  },
  "/files/progress": {
    "stream_response": True
  },
}
