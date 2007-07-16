import cherrypy
from Test_controller import Test_controller


class Test_root( Test_controller ):
  def setUp( self ):
    Test_controller.setUp( self )

  def test_index( self ):
    result = self.http_get( "/" )
    assert result

  def test_next_id( self ):
    result = self.http_get( "/next_id" )

    assert result.get( "next_id" )

    result = self.http_get( "/next_id" )

    assert result.get( "next_id" )

  def test_404( self ):
    result = self.http_get( "/four_oh_four" )

    body = result.get( u"body" )
    assert len( body ) > 0
    assert u"404" in body[ 0 ]

    status = result.get( u"status" )
    assert u"404" in status

    headers = result.get( u"headers" )
    status = headers.get( u"status" )
    assert u"404" in status
