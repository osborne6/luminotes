from Print_notes import Print_notes


def export( database, notebook, notes, response_headers ):
  """
  Format the given notes for printing by relying on controller.Expose.expose() to use Print_notes
  as the view.
  """
  return dict(
    notebook = notebook,
    notes = notes,
    view = Print_notes,
    manual_encode = u"utf8",
  )
