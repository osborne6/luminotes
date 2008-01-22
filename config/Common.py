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
    "luminotes.payment_email": "seller_1199677742_biz@luminotes.com",
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
          <form action="https://www.sandbox.paypal.com/cgi-bin/webscr" method="post" target="_top" class="subscribe_form">
          <input type="image" src="https://www.sandbox.paypal.com/en_US/i/btn/x-click-but24.gif" border="0" name="submit" alt="Make payments with PayPal - it's fast, free and secure!">
          <img alt="" border="0" src="https://www.sandbox.paypal.com/en_US/i/scr/pixel.gif" width="1" height="1">
          <input type="hidden" name="cmd" value="_xclick-subscriptions">
          <input type="hidden" name="business" value="seller_1199677742_biz@luminotes.com">
          <input type="hidden" name="item_name" value="Luminotes Basic">
          <input type="hidden" name="item_number" value="1">
          <input type="hidden" name="no_shipping" value="1">
          <input type="hidden" name="no_note" value="1">
          <input type="hidden" name="currency_code" value="USD">
          <input type="hidden" name="lc" value="US">
          <input type="hidden" name="bn" value="PP-SubscriptionsBF">
          <input type="hidden" name="a3" value="5.00">
          <input type="hidden" name="p3" value="1">
          <input type="hidden" name="t3" value="M">
          <input type="hidden" name="src" value="1">
          <input type="hidden" name="sra" value="1">
          <input type="hidden" name="custom" value="%s">
          <input type="hidden" name="modify" value="1">
          <input type="hidden" name="return" value="http://luminotes.com:8083/users/thanks">
          <input type="hidden" name="cancel_return" value="http://luminotes.com:8083/">
          <input type="hidden" name="rm" value="2">
          <input type="hidden" name="cbt" value="Return to Luminotes">
          </form>
          """,
      },
      {
        "name": "standard",
        "storage_quota_bytes": 500 * MEGABYTE,
        "notebook_collaboration": True,
        "fee": 9,
        "button":
          """
          <form action="https://www.sandbox.paypal.com/cgi-bin/webscr" method="post" target="_top" class="subscribe_form">
          <input type="image" src="https://www.sandbox.paypal.com/en_US/i/btn/x-click-but24.gif" border="0" name="submit" alt="Make payments with PayPal - it's fast, free and secure!">
          <img alt="" border="0" src="https://www.sandbox.paypal.com/en_US/i/scr/pixel.gif" width="1" height="1">
          <input type="hidden" name="cmd" value="_xclick-subscriptions">
          <input type="hidden" name="business" value="seller_1199677742_biz@luminotes.com">
          <input type="hidden" name="item_name" value="Luminotes Standard">
          <input type="hidden" name="item_number" value="2">
          <input type="hidden" name="no_shipping" value="1">
          <input type="hidden" name="no_note" value="1">
          <input type="hidden" name="currency_code" value="USD">
          <input type="hidden" name="lc" value="US">
          <input type="hidden" name="bn" value="PP-SubscriptionsBF">
          <input type="hidden" name="a3" value="9.00">
          <input type="hidden" name="p3" value="1">
          <input type="hidden" name="t3" value="M">
          <input type="hidden" name="src" value="1">
          <input type="hidden" name="sra" value="1">
          <input type="hidden" name="custom" value="%s">
          <input type="hidden" name="modify" value="1">
          <input type="hidden" name="return" value="http://luminotes.com:8083/users/thanks">
          <input type="hidden" name="cancel_return" value="http://luminotes.com:8083/">
          <input type="hidden" name="rm" value="2">
          <input type="hidden" name="cbt" value="Return to Luminotes">
          </form>
          """,
      },
#      {
#        "name": "premium",
#        "storage_quota_bytes": 2000 * MEGABYTE,
#        "notebook_collaboration": True,
#        "fee": 19,
#        "button":
#          """
#          """,
#      },
    ],
    "luminotes.unsubscribe_button":
      """
      <a href="https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_subscr-find&alias=seller_1199677742_biz%40luminotes%2ecom" target="_top">
      <img src="https://www.sandbox.paypal.com/en_US/i/btn/cancel_subscribe_gen_2_new.gif" border="0" alt="Unsubscribe">
      </a>
      """,
  },
}
