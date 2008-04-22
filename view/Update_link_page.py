from Tags import Html, Head, Title, Body, A


class Update_link_page( Html ):
  def __init__( self, notebook_id, notebook_name, note_id, https_url ):
    if notebook_name == u"Luminotes":
      notebook_path = u"/"
    elif notebook_name == u"Luminotes user guide":
      notebook_path = u"/guide"
    elif notebook_name == u"Luminotes blog":
      notebook_path = u"/blog"
    else:
      notebook_path = u"/notebooks/%s" % notebook_id

    notebook_path = https_url + notebook_path

    Html.__init__(
      self,
      Head(
        Title( "Note updated" ),
      ),
      Body(
        u"A note in ",
        A( u"this notebook", href = notebook_path ),
        u"has been updated.",
        A( u"View the note.", href = u"%s?note_id=%s" % ( notebook_path, note_id ) ),
      ),
    )
