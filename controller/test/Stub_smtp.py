class Stub_smtp( object ):
  """
  A stub intended to replace smtplib.SMTP for unit testing code that depends on it.
  """
  connected = False
  from_address = None
  to_addresses = None
  message = None

  def connect( self ):
    Stub_smtp.connected = True

  def sendmail( self, from_address, to_addresses, message ):
    if not Stub_smtp.connected:
      raise Exception( "not connected to the server" )

    Stub_smtp.from_address = from_address
    Stub_smtp.to_addresses = to_addresses
    Stub_smtp.message = message

  def quit( self ):
    Stub_smtp.connected = False

  @staticmethod
  def reset():
    Stub_smtp.connected = False
    Stub_smtp.from_address = None
    Stub_smtp.to_addresses = None
    Stub_smtp.message = None
