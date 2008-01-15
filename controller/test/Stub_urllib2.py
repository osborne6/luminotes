from StringIO import StringIO


result = u"VERIFIED"
headers = None
url = None
encodeded_params = None


class Request( object ):
  def __init__( self, url ):
    global result, headers
    headers = {}

  def add_header( self, key, value ):
    headers[ key ] = value


def urlopen( open_url, params ):
  global url
  global encoded_params

  url = open_url
  encoded_params = params

  return StringIO( result )
