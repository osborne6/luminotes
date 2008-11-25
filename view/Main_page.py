from urllib import urlencode
from cgi import escape
from Page import Page
from Header import Header
from Tags import Link, Input, Div, Span, H2, H4, A, Br, Strong, Script, Img, P, Noscript
from Note_tree_area import Note_tree_area
from Link_area import Link_area
from Toolbar import Toolbar
from Json import Json
from Rounded_div import Rounded_div
from config.Version import VERSION
from model.Notebook import Notebook
from Page_navigation import Page_navigation


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
    invites = None,
    invite_id = None,
    after_login = None,
    signup_plan = None,
    signup_yearly = None,
    recent_notes = None,
    groups = None,
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
      u"user_id": startup_note.user_id,
      u"username": startup_note.username,
    } for startup_note in startup_notes ]

    note_dicts = [ {
      u"object_id" : note.object_id,
      u"revision" : note.revision,
      u"deleted_from_id" : note.deleted_from_id,
      u"user_id": note.user_id,
      u"username": note.username,
      u"creation" : note.creation,
    } for note in notes ]

    root_notes = startup_notes + ( notes and [ note for note in notes if note.object_id not in startup_note_ids ] or [] )

    def json( string ):
      return escape( unicode( Json( string ) ), quote = True )

    if len( notes ) == 1:
      title = notes[ 0 ].title
    else:
      title = notebook.name

    if rate_plan.get( u"notebook_sharing" ):
      updates_path = u"/notebooks/updates/%s?rss&%s" % (
        notebook.object_id,
        urlencode( [ ( u"notebook_name", notebook.name.encode( "utf8" ) ) ] ),
      )
    else:
      updates_path = None

    forum_tags = [ tag for tag in notebook.tags if tag.name == u"forum" ]
    forum_tag = None

    if notebook.name == u"Luminotes":
      notebook_path = u"/"
      updates_path = None   # no RSS feed for the main notebook
    elif notebook.name == u"Luminotes user guide":
      notebook_path = u"/guide"
    elif forum_tags:
      forum_tag = forum_tags[ 0 ]
      if forum_tag.value == u"blog":
        notebook_path = u"/blog/%s" % notebook.friendly_id
      else:
        notebook_path = u"/forums/%s/%s" % ( forum_tag.value, notebook.object_id )
    else:
      notebook_path = u"/notebooks/%s" % notebook.object_id

    conversion_js = None

    if conversion:
      try:
        conversion_js = file( u"static/js/%s_conversion.js" % conversion ).read()
      except IOError:
        pass

    if notebook.read_write == Notebook.READ_WRITE:
      header_note_title = u"wiki"
    else:
      all_notes = startup_notes + notes
      header_note_title = ( notebook.name == "Luminotes" ) and all_notes and all_notes[ 0 ].title or notebook.name
      header_note_title = {
        "contact info": "contact",
        "meet the team": "team",
        "Luminotes user guide": "guide",
        "Luminotes privacy policy": "privacy",
      }.get( header_note_title, header_note_title )

    own_notebooks = [ nb for nb in notebooks if nb.read_write == Notebook.READ_WRITE ]
    header_notebook = own_notebooks and own_notebooks[ 0 ] or notebook

    Page.__init__(
      self,
      title,
      Link( rel = u"stylesheet", type = u"text/css", href = u"/static/css/header.css" ),
      updates_path and \
        Link( rel = u"alternate", type = u"application/rss+xml", title = notebook.name, href = updates_path ) or None,
      Script( type = u"text/javascript", src = u"/static/js/MochiKit.js" ) or None,
      Script( type = u"text/javascript", src = u"/static/js/Invoker.js" ) or None,
      Script( type = u"text/javascript", src = u"/static/js/Editor.js" ) or None,
      Script( type = u"text/javascript", src = u"/static/js/Wiki.js" ) or None,
      Input( type = u"hidden", name = u"user", id = u"user", value = json( user ) ),
      Input( type = u"hidden", name = u"rate_plan", id = u"rate_plan", value = json( rate_plan ) ),
      Input( type = u"hidden", name = u"yearly", id = u"yearly", value = json( signup_yearly ) ),
      Input( type = u"hidden", name = u"notebooks", id = u"notebooks", value = json( notebooks ) ),
      Input( type = u"hidden", name = u"notebook", id = u"notebook", value = json( notebook ) ),
      Input( type = u"hidden", name = u"parent_id", id = u"parent_id", value = parent_id or "" ),
      Input( type = u"hidden", name = u"startup_notes", id = u"startup_notes", value = json( startup_note_dicts ) ),
      Input( type = u"hidden", name = u"current_notes", id = u"current_notes", value = json( note_dicts ) ),
      Input( type = u"hidden", name = u"note_read_write", id = u"note_read_write", value = json( note_read_write ) ),
      Input( type = u"hidden", name = u"rename", id = u"rename", value = json( rename ) ),
      Input( type = u"hidden", name = u"deleted_id", id = u"deleted_id", value = deleted_id ),
      Input( type = u"hidden", name = u"invites", id = u"invites", value = json( invites ) ),
      Input( type = u"hidden", name = u"invite_id", id = u"invite_id", value = invite_id ),
      Input( type = u"hidden", name = u"after_login", id = u"after_login", value = after_login ),
      Input( type = u"hidden", name = u"signup_plan", id = u"signup_plan", value = signup_plan ),
      Input( type = u"hidden", name = u"groups", id = u"groups", value = json( groups ) ),
      Div(
        id = u"status_area",
      ),
      Header( user, header_notebook, login_url, logout_url, header_note_title, rate_plan ),
      Div(
        Div(
          Link_area(
            Toolbar(
              notebook,
              hide_toolbar = parent_id or notebook.read_write == Notebook.READ_ONLY,
              note_word = forum_tag and u"post" or u"note",
            ),
            notebooks, notebook, parent_id, notebook_path, updates_path, user, rate_plan,
          ),
          id = u"left_area",
        ),
        Div(
          ( notebook.read_write != Notebook.READ_ONLY ) and Noscript(
            P( Strong(
              u"""
              Luminotes requires JavaScript to be enabled in your web browser in order to edit
              your wiki. Please <a href="/enable_javascript">enable JavaScript</a> before continuing.
              """
            ) ),
          ) or None,
          Rounded_div(
            ( notebook.name == u"trash" ) and u"trash_notebook" or u"current_notebook",
            ( notebook.name == u"Luminotes" and title == u"source code" ) and \
              Strong( "%s %s" % ( notebook.name, VERSION ) ) or \
              Span(
                ( notebook.name == u"trash" or notebook.read_write != Notebook.READ_WRITE ) \
                  and Strong( notebook.name ) \
                  or Span( Strong( notebook.name ), id = u"notebook_header_name", title = "Rename this notebook." ),
              ),
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
              Page_navigation(
                notebook_path, len( notes ), total_notes_count, start, count,
              ),
              Div(
                Span( id = u"notes_top" ),
                id = u"notes",
              ),
              ( notebook.read_write == Notebook.READ_WRITE ) and Div(
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
              ( forum_tag and user.username and user.username != u"anonymous" ) and \
                P( u"To write a comment, click that large \"+\" button to the left. To publish your comment, click the save button.", class_ = u"small_text" ) or None,
              Page_navigation(
                notebook_path, len( notes ), total_notes_count, start, count,
                return_text = u"return to the discussion",
              ),
              id = u"notebook_background",
              corners = ( u"tl", ),
            ),
            id = u"notebook_border",
            class_ = ( notebook.name == u"trash" ) and u"trash_notebook_color" or u"current_notebook_color",
          ),
          id = u"center_content_area",
        ),
        Div(
          Note_tree_area(
            notebook,
            root_notes,
            recent_notes,
            total_notes_count,
            user,
          ),
          id = u"right_area",
        ),
        id = u"everything_area",
      ),
    )
