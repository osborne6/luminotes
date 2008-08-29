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
    "luminotes.db_host": "localhost", # hostname for PostgreSQL or None (no quotes) for SQLite
    "luminotes.db_ssl_mode": "allow", # "disallow", "allow", "prefer", or "require"
    "luminotes.support_email": "",
    "luminotes.payment_email": "",
    "luminotes.rate_plans": [
      {
        "name": "free",
        "designed_for": "students",
        "storage_quota_bytes": 30 * MEGABYTE,
        "included_users": 1,
        "notebook_sharing": True,
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
        "notebook_sharing": True,
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
        "notebook_sharing": True,
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
        "notebook_sharing": True,
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
        "notebook_sharing": True,
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
    "luminotes.download_button":
      """
      <form action="https://www.paypal.com/cgi-bin/webscr" method="post">
      <input type="hidden" name="cmd" value="_s-xclick">
      <input type="image" src="/static/images/download_button.png" border="0" name="submit" alt="PayPal - The safer, easier way to pay online!">
      <img alt="" border="0" src="https://www.paypal.com/en_US/i/scr/pixel.gif" width="1" height="1">
      <input type="hidden" name="encrypted" value="-----BEGIN PKCS7-----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-----END PKCS7-----">
      </form>
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
