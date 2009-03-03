from Html_file import Html_file


def export( database, notebook, notes, response_headers ):
  """
  Format the given notes as an HTML file by relying on controller.Expose.expose() to use Html_file
  as the view.
  """
  return dict(
    notebook = notebook,
    notes = notes,
    response_headers = response_headers,
    view = Html_file,
    manual_encode = u"utf8",
  )
