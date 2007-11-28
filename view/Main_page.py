from cgi import escape
from Page import Page
from Tags import Input, Div, Span, H2, H4, A, Br, Strong, Script, Img
from Search_form import Search_form
from User_area import User_area
from Link_area import Link_area
from Toolbar import Toolbar
from Json import Json
from Rounded_div import Rounded_div


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
    notes = None,
    note_read_write = True,
    start = None,
    count = None,
    http_url = None,
    conversion = None,
    rename = False,
    deleted_id = None,
  ):
    startup_note_ids = [ startup_note.object_id for startup_note in startup_notes ]

    static_notes = Div(
      notes and [ Div(
        note.contents,
        id = "static_note_%s" % note.object_id,
      ) for note in notes ] or
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

    note_dicts = [ {
      u"object_id" : note.object_id,
      u"revision" : note.revision,
      u"deleted_from_id" : note.deleted_from_id,
      u"creation" : note.creation,
    } for note in notes ]

    def json( string ):
      return escape( unicode( Json( string ) ), quote = True )

    if len( notes ) == 1:
      title = notes[ 0 ].title
    else:
      title = None

    if notebook.name == u"Luminotes":
      notebook_path = u"/"
    elif notebook.name == u"Luminotes user guide":
      notebook_path = u"/guide"
    elif notebook.name == u"Luminotes blog":
      notebook_path = u"/blog"
    else:
      notebook_path = u"/notebooks/%s" % notebook.object_id

    conversion_html = None

    if conversion:
      try:
        conversion_html = file( u"static/html/%s_conversion.html" % conversion ).read()
      except IOError:
        pass

    Page.__init__(
      self,
      title,
      Input( type = u"hidden", name = u"storage_bytes", id = u"storage_bytes", value = user.storage_bytes ),
      Input( type = u"hidden", name = u"rate_plan", id = u"rate_plan", value = json( rate_plan ) ),
      Input( type = u"hidden", name = u"notebooks", id = u"notebooks", value = json( notebooks ) ),
      Input( type = u"hidden", name = u"notebook_id", id = u"notebook_id", value = notebook.object_id ),
      Input( type = u"hidden", name = u"parent_id", id = u"parent_id", value = parent_id or "" ),
      Input( type = u"hidden", name = u"startup_notes", id = u"startup_notes", value = json( startup_note_dicts ) ),
      Input( type = u"hidden", name = u"current_notes", id = u"current_notes", value = json( note_dicts ) ),
      Input( type = u"hidden", name = u"note_read_write", id = u"note_read_write", value = json( note_read_write ) ),
      Input( type = u"hidden", name = u"rename", id = u"rename", value = json( rename ) ),
      Input( type = u"hidden", name = u"deleted_id", id = u"deleted_id", value = deleted_id ),
      Div(
        id = u"status_area",
      ),
      Div(
        Div(
          Br(),
          Toolbar( hide_toolbar = not notebook.read_write ),
          id = u"toolbar_area",
        ),
        Link_area( notebooks, notebook, total_notes_count, parent_id, notebook_path, user ),
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
              A( Img( src = "/static/images/luminotes_title.png" ), href = "/", title = "Luminotes personal wiki notebook" ),
              id = u"title_area",
            ),
            id = u"top_area",
          ),
          Rounded_div(
            ( notebook.name == u"trash" ) and u"trash_notebook" or u"current_notebook",
            ( notebook.name == u"trash" or not notebook.read_write ) \
              and (
                len( notes ) == 1 and A( Strong( notebook.name ), href = notebook_path ) or Strong( notebook.name )
              ) \
              or Span( Strong( notebook.name ), id = u"notebook_header_name" ),
            parent_id and Span(
              u" | ",
              A( u"empty trash", href = u"/notebooks/%s" % notebook.object_id, id = u"empty_trash_link" ),
              u" | ",
              A( u"return to notebook", href = u"/notebooks/%s" % parent_id ),
            ) or None,
            id = u"notebook_header_area",
            corners = ( u"tl", u"tr", u"br" ),
          ),
          Div(
            Rounded_div(
              ( notebook.name == u"trash" ) and u"trash_notebook_inner" or u"current_notebook_inner",
              Div(
                id = u"deleted_notebooks",
              ),
              Div(
                Span( id = u"notes_top" ),
                id = u"notes",
              ),
              notebook.read_write and Div(
                id = u"blank_note_stub",
                class_ = u"blank_note_stub_hidden_border",
              ) or None,
              static_notes,
              # Sort of simulate the <noscript> tag by hiding the static version of the notes.
              # This code won't be executed if JavaScript is disabled. I'm not actually using
              # <noscript> because I want to be able to programmatically read the hidden static
              # notes when JavaScript is enabled.
              Script(
                u"document.getElementById( 'static_notes' ).style.display = 'none';",
                type = u"text/javascript",
              ),
              # make page navigation for those notebooks that require it (such as the blog)
              ( start is not None and count is not None and len( notes ) > 1 ) and Div(
                ( start > 0 ) and Div( A(
                  u"previous page",
                  href = "%s?start=%d&count=%d" % ( notebook_path, max( start - count, 0 ), count ),
                ) ) or None,
                ( start + count < total_notes_count ) and Div( A(
                  u"next page",
                  href = "%s?start=%d&count=%d" % ( notebook_path, min( start + count, total_notes_count - 1 ), count ),
                ) ) or None,
              ) or None,
              id = u"notebook_background",
              corners = ( u"tl", ),
            ),
            id = u"notebook_border",
            class_ = ( notebook.name == u"trash" ) and u"trash_notebook_color" or u"current_notebook_color",
          ),
          id = u"center_area",
        ),
        Div(
          conversion_html,
          id = u"conversion_area",
        ),
        id = u"everything_area",
      ),
    )
