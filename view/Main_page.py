from cgi import escape
from Page import Page
from Tags import Input, Div, Span, H2, H4, A, Br, Strong, Script
from Search_form import Search_form
from User_area import User_area
from Link_area import Link_area
from Toolbar import Toolbar
from Json import Json


class Main_page( Page ):
  def __init__(
    self,
    user,
    rate_plan,
    notebooks,
    notebook,
    parent_id = None,
    login_url = None,
    logout_url = None,
    startup_notes = None,
    total_notes_count = None,
    note = None,
    note_read_write = True,
  ):
    startup_note_ids = [ startup_note.object_id for startup_note in startup_notes ]

    static_notes = Div(
      note and Div(
        note.contents,
        id = "static_note_%s" % note.object_id,
      ) or
      [ Div(
        startup_note.contents,
        id = "static_note_%s" % startup_note.object_id
      ) for startup_note in startup_notes ],
      id = "static_notes",
    )

    # Since the contents of these notes are included in the static_notes section below, don't
    # include them again in the hidden fields here. Accomplish this by making custom dicts for
    # sending to the client.
    startup_note_dicts = [ {
      u"object_id" : startup_note.object_id,
      u"revision" : startup_note.revision,
      u"deleted_from_id" : startup_note.deleted_from_id,
    } for startup_note in startup_notes ]

    if note:
      note_dict = {
        u"object_id" : note.object_id,
        u"revision" : note.revision,
        u"deleted_from_id" : note.deleted_from_id,
      }

    def json( string ):
      return escape( unicode( Json( string ) ), quote = True )

    title = None
    Page.__init__(
      self,
      title,
      Input( type = u"hidden", name = u"storage_bytes", id = u"storage_bytes", value = user.storage_bytes ),
      Input( type = u"hidden", name = u"rate_plan", id = u"rate_plan", value = json( rate_plan ) ),
      Input( type = u"hidden", name = u"notebooks", id = u"notebooks", value = json( notebooks ) ),
      Input( type = u"hidden", name = u"notebook_id", id = u"notebook_id", value = notebook.object_id ),
      Input( type = u"hidden", name = u"parent_id", id = u"parent_id", value = parent_id or "" ),
      Input( type = u"hidden", name = u"startup_notes", id = u"startup_notes", value = json( startup_note_dicts ) ),
      Input( type = u"hidden", name = u"note", id = u"note", value = note and json( note_dict ) or "" ),
      Input( type = u"hidden", name = u"note_read_write", id = u"note_read_write", value = json( note_read_write ) ),
      Div(
        id = u"status_area",
      ),
      Div(
        Div(
          Br(),
          Toolbar( hide_toolbar = not notebook.read_write ),
          id = u"toolbar_area",
        ),
        Link_area( notebooks, notebook, total_notes_count, parent_id ),
        Div(
          Div(
            Div(
              User_area( user, login_url, logout_url ),
              Div(
                Search_form(),
                id = u"search_area",
              ),
              id = u"search_and_user_area",
            ),
            Div(
              H2( A( u"Luminotes", href = "/" ), class_ = "page_title" ),
              H4( A( u"personal wiki notebook", href = "/" ), class_ = u"page_title" ),
              id = u"title_area",
            ),
            id = u"top_area",
          ),
          Div(
            Strong( notebook.name ),
            parent_id and Span(
              u" | ",
              A( u"empty trash", href = u"/notebooks/%s" % notebook.object_id, id = u"empty_trash_link" ),
              u" | ",
              A( u"return to notebook", href = u"/notebooks/%s" % parent_id ),
            ) or None,
            id = u"notebook_header_area",
            class_ = ( notebook.name == u"trash" ) and u"current_trash_notebook_name" or u"current_notebook_name",
          ),
          Div(
            Div(
              Div(
                id = u"notes",
              ),
              static_notes,
              # Sort of simulate the <noscript> tag by hiding the static version of the notes.
              # This code won't be executed if JavaScript is disabled. I'm not actually using
              # <noscript> because I want to be able to programmatically read the hidden static
              # notes when JavaScript is enabled.
              Script(
                u"document.getElementById( 'static_notes' ).style.display = 'none';",
                type = u"text/javascript",
              ),
              id = u"notebook_background",
            ),
            id = u"notebook_border",
            class_ = ( notebook.name == u"trash" ) and u"current_trash_notebook_name" or u"current_notebook_name",
          ),
          id = u"center_area",
        ),
        id = u"everything_area",
      ),
    )
