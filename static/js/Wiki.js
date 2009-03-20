IMAGE_DIR = "/static/images/";
NOTEBOOK_READ_ONLY = 0;
NOTEBOOK_READ_WRITE = 1;
NOTEBOOK_READ_WRITE_FOR_OWN_NOTES = 2;


function Wiki( invoker ) {
  this.next_id = null;
  this.focused_editor = null;
  this.notebook = evalJSON( getElement( "notebook" ).value );
  this.parent_id = getElement( "parent_id" ).value; // id of the notebook containing this one
  this.startup_notes = new Array();  // map of startup notes: note id to bool
  this.open_editors = new Array();   // map of open notes: lowercase note title to editor
  this.search_results_editor = null; // editor for display of search results
  this.invoker = invoker;
  this.user = evalJSON( getElement( "user" ).value );
  this.rate_plan = evalJSON( getElement( "rate_plan" ).value );
  this.yearly = evalJSON( getElement( "yearly" ).value );
  this.storage_usage_high = false;
  this.invites = evalJSON( getElement( "invites" ).value );
  this.invite_id = getElement( "invite_id" ).value;
  this.after_login = getElement( "after_login" ).value;
  this.signup_plan = getElement( "signup_plan" ).value;
  this.groups = evalJSON( getElement( "groups" ).value );
  this.font_size = null;
  this.small_toolbar = false;
  this.large_toolbar_bottom = 0;
  this.autosaver = null;

  var total_notes_count_node = getElement( "total_notes_count" );
  if ( total_notes_count_node )
    this.total_notes_count = parseInt( scrapeText( total_notes_count_node ) );
  else
    this.total_notes_count = null;

  if ( getElement( "note_tree_root_table" ) )
    this.note_tree = new Note_tree( this, this.notebook.object_id, this.invoker );
  this.recent_notes = new Recent_notes( this, this.notebook.object_id, this.invoker );

  this.notebooks = evalJSON( getElement( "notebooks" ).value );
  this.notebooks_by_id = {};

  for ( var i in this.notebooks ) {
    var notebook = this.notebooks[ i ];

    if ( !this.notebooks_by_id[ notebook.object_id ] )
      this.notebooks_by_id[ notebook.object_id ] = notebook;
  }

  if ( this.notebook && this.notebook.read_write != NOTEBOOK_READ_ONLY ) {
    var unsupported_agent = null;
    var beta_agent = null;

    if ( OPERA )
      unsupported_agent = "Opera";
    else if ( MSIE6 )
      unsupported_agent = "Microsoft Internet Explorer version 6";

    if ( unsupported_agent )
      this.display_message( "Luminotes does not currently support the " + unsupported_agent + " web browser for editing. If possible, please use a recent version of Firefox, Internet Explorer, Chrome, or Safari instead. Sorry for the inconvenience." );
    else if ( beta_agent )
      this.display_message( "Luminotes support for your web browser (" + beta_agent + ") is currently in beta. If you encounter any problems, please contact support so that they can be fixed!" );
  }

  if ( !this.notebook_has_tag( this.notebook, "forum" ) )
    this.autosaver = Autosaver( this );

  var deleted_id = getElement( "deleted_id" ).value;
  var skip_empty_message = deleted_id ? true : false;

  // populate the wiki with startup notes
  this.populate(
    evalJSON( getElement( "startup_notes" ).value || "null" ),
    evalJSON( getElement( "current_notes" ).value || "null" ),
    evalJSON( getElement( "note_read_write" ).value || "true" ),
    skip_empty_message
  );

  this.display_storage_usage( this.user.storage_bytes || "0" );

  connect( this.invoker, "error_message", this, "display_error" );
  connect( this.invoker, "message", this, "display_message" );
  connect( "search_form", "onsubmit", this, "search" );
  connect( "search_text", "onfocus", this, "search_focused" );
  connect( "search_text", "onblur", this, "search_blurred" );
  connect( "search_text", "onkeyup", this, "search_key_released" );
  connect( "html", "onclick", this, "background_clicked" );
  connect( "html", "onkeydown", this, "key_pressed" );
  connect( window, "onresize", this, "resize_editor" );
  connect( window, "onresize", this, "resize_toolbar" );
  connect( document, "onmouseover", this, "detect_font_resize" );

  var blank_note_stub = getElement( "blank_note_stub" );
  if ( blank_note_stub ) {
    connect( blank_note_stub, "onmouseover", function ( event ) {
      addElementClass( blank_note_stub, "blank_note_stub_border" );
      removeElementClass( blank_note_stub, "blank_note_stub_hidden_border" );
    } );
    connect( blank_note_stub, "onmouseout", function ( event ) {
      addElementClass( blank_note_stub, "blank_note_stub_hidden_border" );
      removeElementClass( blank_note_stub, "blank_note_stub_border" );
    } );
    connect( blank_note_stub, "onclick", this, "create_blank_editor" );
  }

  var self = this;
  var top_window = window;
  var logout_link = getElement( "logout_link" );
  if ( logout_link ) {
    connect( "logout_link", "onclick", function ( event ) {
      self.save_editor( null, false, function () {
        top_window.location = "/users/logout";
      } );
      event.stop();
    } );
  }

  var rename = evalJSON( getElement( "rename" ).value );
  if ( rename && this.notebook.read_write == NOTEBOOK_READ_WRITE )
    this.start_notebook_rename();

  // if a notebook was just deleted, show a message with an undo button
  if ( deleted_id && this.notebook.read_write == NOTEBOOK_READ_WRITE ) {
    var undo_button = createDOM( "input", {
      "type": "button",
      "class": "message_button",
      "value": "undo",
      "title": "undo deletion"
    } );
    var trash_link = createDOM( "a", {
      "href": "/notebooks/" + this.notebook.trash_id + "?parent_id=" + this.notebook.object_id
    }, "trash" );
    var message_div = this.display_message( "The notebook has been moved to the", [ trash_link, ". ", undo_button ], "notes_top" );
    connect( undo_button, "onclick", function ( event ) { self.undelete_notebook( event, deleted_id ); } );
  }

  var current_notebook_up = getElement( "current_notebook_up" );
  if ( current_notebook_up ) {
    connect( current_notebook_up, "onmouseover", function ( event ) { current_notebook_up.src = IMAGE_DIR + "up_arrow_hover.png"; } );
    connect( current_notebook_up, "onmouseout", function ( event ) { current_notebook_up.src = IMAGE_DIR + "up_arrow.png"; } );
    connect( current_notebook_up, "onclick", function ( event ) {
      current_notebook_up.src = IMAGE_DIR + "up_arrow.png";
      self.move_current_notebook_up( event );
    } );
  }

  var current_notebook_down = getElement( "current_notebook_down" );
  if ( current_notebook_down ) {
    connect( current_notebook_down, "onmouseover", function ( event ) { current_notebook_down.src = IMAGE_DIR + "down_arrow_hover.png"; } );
    connect( current_notebook_down, "onmouseout", function ( event ) { current_notebook_down.src = IMAGE_DIR + "down_arrow.png"; } );
    connect( current_notebook_down, "onclick", function ( event ) {
      current_notebook_down.src = IMAGE_DIR + "down_arrow.png";
      self.move_current_notebook_down( event );
    } );
  }

  this.resize_toolbar();
}

Wiki.prototype.update_next_id = function ( result ) {
  this.next_id = result.next_id;
}

var KILOBYTE = 1024;
var MEGABYTE = 1024 * KILOBYTE;
function bytes_to_megabytes( bytes, choose_units ) {
  if ( choose_units ) {
    if ( bytes < KILOBYTE )
      return bytes + " bytes";
    if ( bytes < MEGABYTE )
      return Math.round( bytes / KILOBYTE ) + " KB";
  }

  return Math.round( bytes / MEGABYTE ) + " MB";
}

Wiki.prototype.display_storage_usage = function( storage_bytes ) {
  if ( !storage_bytes )
    return;

  // display the user's current storage usage
  var quota_bytes = this.rate_plan.storage_quota_bytes;
  if ( !quota_bytes )
    return;

  var usage_percent = Math.round( storage_bytes / quota_bytes * 100.0 );

  if ( usage_percent > 90 ) {
    var storage_usage_class = "storage_usage_high";
    if ( this.storage_usage_high == false )
      this.display_message(
        "You are currently using " +
        usage_percent +
        "% of your available storage space. Please delete some notes or files, empty the trash, or",
        [ createDOM( "a", { "href": "/upgrade" }, "upgrade" ), " your account." ]
      );
    this.storage_usage_high = true;
  } else if ( usage_percent > 75 ) {
    var storage_usage_class = "storage_usage_medium";
    this.storage_usage_high = false;
  } else {
    var storage_usage_class = "storage_usage_low";
    this.storage_usage_high = false;
  }

  var storage_usage_area = getElement( "storage_usage_area" );
  if ( !storage_usage_area )
    return;

  replaceChildNodes(
    storage_usage_area,
    createDOM( "div", { "class": storage_usage_class },
    bytes_to_megabytes( storage_bytes ) + " (" + usage_percent + "%) of " + bytes_to_megabytes( quota_bytes ) )
  );
}

Wiki.prototype.populate = function ( startup_notes, current_notes, note_read_write, skip_empty_message ) {
  var self = this;

  // if this is the trash and the user has owner-level access, then display a list of all deleted notebooks
  if ( this.notebook.owner && this.notebook.name == "trash" ) {
    var heading_shown = false;
    var deleted_notebooks = getElement( "deleted_notebooks" );

    for ( var i in this.notebooks ) {
      var notebook = this.notebooks[ i ];
      if ( !notebook.deleted )
        continue;

      if ( !heading_shown ) {
        appendChildNodes( deleted_notebooks, createDOM( "h4", {}, "deleted notebooks" ) );
        heading_shown = true;
      }

      delete_button = createDOM( "input", {
        "type": "button",
        "class": "note_button",
        "id": "delete_notebook_" + notebook.object_id,
        "value": "delete forever",
        "title": "delete notebook"
      } );
      function connect_delete( notebook_id ) {
        connect( delete_button, "onclick", function ( event ) { self.delete_notebook_forever( event, notebook_id ); } );
      }
      connect_delete( notebook.object_id );

      undelete_button = createDOM( "input", {
        "type": "button",
        "class": "note_button",
        "id": "undelete_notebook_" + notebook.object_id,
        "value": "undelete",
        "title": "undelete notebook"
      } );
      function connect_undelete( notebook_id ) {
        connect( undelete_button, "onclick", function ( event ) { self.undelete_notebook( event, notebook_id ); } );
      }
      connect_undelete( notebook.object_id );

      appendChildNodes( deleted_notebooks, createDOM( "div",
        { "id": "deleted_notebook_" + notebook.object_id, "class": "deleted_notebook_item" },
        createDOM( "span", {}, delete_button ),
        createDOM( "span", {}, undelete_button ),
        createDOM( "span", {}, notebook.name )
      ) );
    }
  }

  // create an editor for each startup note in the received notebook, focusing the first one
  var focus = true;
  for ( var i in startup_notes ) {
    var startup_note = startup_notes[ i ];
    this.startup_notes[ startup_note.object_id ] = true;

    // don't actually create an editor if a particular list of notes was provided in the result
    if ( current_notes.length == 0 ) {
      var static_note = getElement( "static_note_" + startup_note.object_id );
      if ( !static_note ) continue;
      var static_contents = getFirstElementByTagAndClassName( "span", "static_note_contents", static_note );
      if ( !static_contents ) continue;
      var contents_text = static_contents.innerHTML;

      var editor = this.create_editor(
        startup_note.object_id,
        // grab this note's contents from the static notes area
        contents_text,
        startup_note.deleted_from_id,
        startup_note.revision,
        startup_note.creation,
        this.notebook.read_write, false, focus, null,
        startup_note.user_id,
        startup_note.username
      );

      if ( startup_note.title )
        this.open_editors[ startup_note.title.toLowerCase() ] = editor;
      focus = false;
    }
  }

  // if particular notes were provided, then display editors for them
  var focus = true;
  for ( var i in current_notes ) {
    var note = current_notes[ i ];

    if ( !note_read_write )
      var read_write = NOTEBOOK_READ_ONLY;
    else
      var read_write = this.notebook.read_write;

    var static_note = getElement( "static_note_" + note.object_id );
    if ( !static_note ) continue;
    var static_contents = getFirstElementByTagAndClassName( "span", "static_note_contents", static_note );
    if ( !static_contents ) continue;
    var contents_text = static_contents.innerHTML;

    this.create_editor(
      note.object_id,
      contents_text,
      note.deleted_from_id,
      note.revision,
      note.creation,
      read_write, false, focus, null,
      note.user_id,
      note.username
    );
    focus = false;
  }

  if ( startup_notes.length == 0 && current_notes.length == 0 && !skip_empty_message )
    this.display_empty_message();

  var empty_trash_link = getElement( "empty_trash_link" );
  if ( empty_trash_link )
    connect( empty_trash_link, "onclick", function ( event ) { self.delete_all_editors( event ); } );

  if ( this.notebook.read_write != NOTEBOOK_READ_ONLY ) {
    connect( window, "onunload", function ( event ) { self.editor_focused( null, true ); } );
    connect( "newNote", "onclick", this, "create_blank_editor" );
    connect( "createLink", "onclick", this, "toggle_link_button" );
    if ( this.notebook.read_write == NOTEBOOK_READ_WRITE )
      connect( "attachFile", "onclick", this, "toggle_attach_button" );
    connect( "bold", "onclick", function ( event ) { self.toggle_button( event, "bold" ); } );
    connect( "italic", "onclick", function ( event ) { self.toggle_button( event, "italic" ); } );
    connect( "underline", "onclick", function ( event ) { self.toggle_button( event, "underline" ); } );
    connect( "strikethrough", "onclick", function ( event ) { self.toggle_button( event, "strikethrough" ); } );
    connect( "font", "onclick", this, "toggle_font_button" );
    connect( "title", "onclick", function ( event ) { self.toggle_button( event, "title" ); } );
    connect( "insertUnorderedList", "onclick", function ( event ) { self.toggle_button( event, "insertUnorderedList" ); } );
    connect( "insertOrderedList", "onclick", function ( event ) { self.toggle_button( event, "insertOrderedList" ); } );

    this.make_image_button( "newNote", "new_note" );
    this.make_image_button( "createLink", "link" );
    if ( this.notebook.read_write == NOTEBOOK_READ_WRITE )
      this.make_image_button( "attachFile", "attach" );
    this.make_image_button( "bold" );
    this.make_image_button( "italic" );
    this.make_image_button( "underline" );
    this.make_image_button( "strikethrough" );
    this.make_image_button( "font" );
    this.make_image_button( "title" );
    this.make_image_button( "insertUnorderedList", "bullet_list" );
    this.make_image_button( "insertOrderedList", "numbered_list" );

    // grab the next available object id
    this.invoker.invoke( "/next_id", "POST", null,
      function( result ) { self.update_next_id( result ); }
    );
  }

  var save_button = getElement( "save_button" );
  if ( save_button ) {
    connect( save_button, "onclick", function ( event ) {
      self.save_editor( null );
    } );
    save_button.disabled = true;
  }

  var export_link = getElement( "export_link" );
  if ( export_link ) {
    connect( export_link, "onclick", function ( event ) {
      self.save_editor( null );
      self.export_clicked();
      event.stop();
    } );
  }

  var import_link = getElement( "import_link" );
  if ( import_link ) {
    connect( import_link, "onclick", function ( event ) {
      self.import_clicked();
      event.stop();
    } );
  }

  var rename_notebook_link = getElement( "rename_notebook_link" );
  if ( rename_notebook_link ) {
    connect( rename_notebook_link, "onclick", function ( event ) {
      self.start_notebook_rename();
      event.stop();
    } );
  }

  var notebook_header_name = getElement( "notebook_header_name" );
  if ( notebook_header_name ) {
    connect( notebook_header_name, "onclick", function ( event ) {
      self.start_notebook_rename();
      event.stop();
    } );
  }

  var delete_notebook_link = getElement( "delete_notebook_link" );
  if ( delete_notebook_link ) {
    connect( delete_notebook_link, "onclick", function ( event ) {
      self.delete_notebook();
      event.stop();
    } );
  }

  var share_notebook_link = getElement( "share_notebook_link" );
  if ( share_notebook_link ) {
    connect( share_notebook_link, "onclick", function ( event ) {
      self.load_editor( "share this notebook", "null", null, null, null, getElement( "notes_top" ) );
      event.stop();
    } );
  }

  var print_notebook_link = getElement( "print_notebook_link" );
  if ( print_notebook_link ) {
    connect( print_notebook_link, "onclick", function ( event ) {
      self.editor_focused( null, true );
    } );
  }

  var settings_link = getElement( "settings_link" );
  if ( settings_link ) {
    connect( settings_link, "onclick", function ( event ) {
      self.load_editor( "account settings", "null", null, null, null, getElement( "notes_top" ) );
      event.stop();
    } );
  }

  var declutter_link = getElement( "declutter_link" );
  if ( declutter_link ) {
    connect( declutter_link, "onclick", function ( event ) {
      self.declutter_clicked();
      event.stop();
    } );
  }

  var new_notebook_button = getElement( "new_notebook" );
  if ( new_notebook_button ) {
    connect( new_notebook_button, "onclick", function ( event ) {
      self.invoker.invoke( "/notebooks/create", "POST" );
      event.stop();
    } );

    this.make_image_button( "new_notebook", "new_note", true );
  }

  var new_note_tree_link_button = getElement( "new_note_tree_link" );
  if ( new_note_tree_link_button ) {
    connect( new_note_tree_link_button, "onclick", function ( event ) {
      self.clear_pulldowns();
      if ( self.note_tree )
        self.note_tree.start_link_add();
      event.stop();
    } );

    this.make_image_button( "new_note_tree_link", "new_note", true );
  }
}

Wiki.prototype.background_clicked = function ( event ) {
  if ( !event.target().tagName )
    return;

  var tag_name = event.target().tagName.toLowerCase();

  if ( tag_name == "input" || tag_name == "label" )
    return;

  this.clear_pulldowns();
}

Wiki.prototype.create_blank_editor = function ( event ) {
  if ( event ) event.stop();

  if ( this.notebook.read_write == NOTEBOOK_READ_WRITE_FOR_OWN_NOTES &&
       ( !this.user.username || this.user.username == "anonymous" ) ) {
    this.display_message( 'Please login first. No account? Click "sign up" to get a free account.' );
    return;
  }

  this.clear_messages();
  this.clear_pulldowns();

  // if we're within the trash, don't allow new note creation
  if ( this.notebook.name == "trash" ) {
    this.display_error( "You can't create notes in the trash." );
    return;
  }

  // if there is already a blank editor, then highlight it and bail
  if ( Editor.shared_iframe && Editor.shared_iframe.editor() && Editor.shared_iframe.editor().empty() ) {
    Editor.shared_iframe.editor().highlight();
    return;
  }

  var editor = this.create_editor( undefined, undefined, undefined, undefined, undefined, this.notebook.read_write, true, true, null, this.user.object_id, this.user.username );
  this.increment_total_notes_count();
  signal( this, "note_added", editor );
}

Wiki.prototype.load_editor = function ( note_title, note_id, revision, previous_revision, link, position_after ) {
  if ( this.notebook.name == "trash" && !revision ) {
    this.display_message( "If you'd like to use this note, try undeleting it first.", undefined, position_after );
    return;
  }

  // if a link is given with an open link pulldown, then ignore the note title given and use the
  // one from the pulldown instead
  if ( link ) {
    var pulldown = link.pulldown;
    var pulldown_title = undefined;
    if ( pulldown && pulldown.title_field ) {
      pulldown_title = strip( pulldown.title_field.value );
      if ( pulldown_title )
        note_title = pulldown_title;

      // only use the pulldown title if it has changed from the note's original title
      if ( pulldown_title == note_title )
        pulldown_title = undefined;
    }

    if ( link.target )
      link.removeAttribute( "target" );
  }

  // if the note corresponding to the link's id is already open, highlight it and bail, but only if
  // we didn't pull a title from an open link pulldown
  if ( !pulldown_title ) {
    var editor = editor_by_id( note_id, revision );

    if ( editor ) {
      editor.highlight();
      if ( link )
        link.href = "/notebooks/" + this.notebook.object_id + "?note_id=" + note_id;
      return;
    }
  }

  // if there's not a valid destination note id, then load by title instead of by id
  var self = this;
  if ( pulldown_title || note_id == undefined || note_id == "new" || note_id == "null" ) {
    var lower_note_title = note_title.toLowerCase();
  
    // if the note_title corresponds to a "magic" note's title, then dynamically highlight or create the note
    if ( lower_note_title == "search results" ) {
      var editor = this.open_editors[ lower_note_title ];
      if ( editor ) {
        editor.highlight();
        return;
      }

      this.display_search_results();
      return;
    }
    if ( lower_note_title == "share this notebook" ) {
      var editor = this.open_editors[ lower_note_title ];
      if ( editor ) {
        editor.highlight();
        return;
      }

      this.share_notebook();
      return;
    }
    if ( lower_note_title == "account settings" ) {
      var editor = this.open_editors[ lower_note_title ];
      if ( editor ) {
        editor.highlight();
        return;
      }

      this.display_settings();
      return;
    }

    // but if the note corresponding to the link's title is already open, highlight it and bail
    if ( !revision ) {
      var editor = this.open_editors[ lower_note_title ];
      if ( editor ) {
        editor.highlight();
        if ( link )
          link.href = "/notebooks/" + this.notebook.object_id + "?note_id=" + editor.id;
        return;
      }
    }

    // if the notebook is a forum, then instead of opening a new post, display an error message
    if ( this.notebook_has_tag( this.notebook, "forum" ) ) {
      this.display_message( "No such forum post! (A forum link must point to another post in this discussion or an external web page.)" );
      return;
    }

    this.invoker.invoke(
      "/notebooks/load_note_by_title", "GET", {
        "notebook_id": this.notebook.object_id,
        "note_title": note_title,
        "revision": revision
      },
      function ( result ) { self.parse_loaded_editor( result, note_title, revision, link, position_after ); }
    );
    return;
  }

  // if the notebook is a forum, maintain displayed note order by opening an existing note on its own page
  if ( this.notebook_has_tag( this.notebook, "forum" ) ) {
    window.location = window.location.protocol + '//' + window.location.host + window.location.pathname + '?note_id=' + note_id;
    return;
  }

  this.invoker.invoke(
    "/notebooks/load_note", "GET", {
      "notebook_id": this.notebook.object_id,
      "note_id": note_id,
      "revision": revision,
      "previous_revision": previous_revision
    },
    function ( result ) { self.parse_loaded_editor( result, note_title, revision, link, position_after ); }
  );
}

Wiki.prototype.resolve_link = function ( note_title, link, force, callback ) {
  // if the title looks like a URL, then make it a link to an external site
  if ( /^\w+:\/\//.test( note_title ) || /^mailto:/.test( note_title ) )
    var title_looks_like_url = true;
  else
    var title_looks_like_url = false;

  if ( link && link.target )
    link.removeAttribute( "target" );

  if ( note_title == "search results" || note_title == "share this notebook" || note_title == "account settings" ) {
    link.href = "/notebooks/" + this.notebook.object_id + "?" + queryString(
      [ "title", "note_id" ],
      [ note_title, "null" ]
    );
    if ( callback ) {
      if ( note_title == "search results" )
        callback( "current search results" );
      else if ( note_title == "share this notebook" )
        callback( "share this notebook with others" );
      else
        callback( "account settings" );
    }
    return;
  }

  var id = parse_query( link ).note_id;

  // if the link already has a valid-looking id, it's already resolved, so bail
  if ( !force && id != undefined && id != "new" && id != "null" ) {
    if ( callback )
      callback( null );
    return;
  }

  if ( note_title.length == 0 )
    return;

  // if the note corresponding to the link's title is already open, resolve the link and bail
  var editor = this.open_editors[ note_title.toLowerCase() ];
  if ( editor ) {
    if ( link )
      link.href = "/notebooks/" + this.notebook.object_id + "?note_id=" + editor.id;
    if ( callback )
      callback( editor.summarize() );
    return;
  }

  var self = this;
  if ( callback ) {
    this.invoker.invoke(
      "/notebooks/load_note_by_title", "GET", {
        "notebook_id": this.notebook.object_id,
        "note_title": note_title,
        "summarize": true
      },
      function ( result ) {
        if ( result && result.note ) {
          link.href = "/notebooks/" + self.notebook.object_id + "?note_id=" + result.note.object_id;
        } else if ( title_looks_like_url ) {
          link.target = "_new";
          link.href = note_title;
          callback( "web link" );
          return;
        } else {
          link.href = "/notebooks/" + self.notebook.object_id + "?" + queryString(
            [ "title", "note_id" ],
            [ note_title, "null" ]
          );
        }

        callback( ( result && result.note ) ? result.note.summary : null );
      }
    );
    return;
  }

  this.invoker.invoke(
    "/notebooks/lookup_note_id", "GET", {
      "notebook_id": this.notebook.object_id,
      "note_title": note_title
    },
    function ( result ) {
      if ( result && result.note_id ) {
        link.href = "/notebooks/" + self.notebook.object_id + "?note_id=" + result.note_id;
      } else if ( title_looks_like_url ) {
        link.target = "_new";
        link.href = note_title;
      } else {
        link.href = "/notebooks/" + self.notebook.object_id + "?" + queryString(
          [ "title", "note_id" ],
          [ note_title, "null" ]
        );
      }
    }
  );
}

Wiki.prototype.parse_loaded_editor = function ( result, note_title, requested_revision, link, position_after ) {
  if ( result.note_id_in_trash ) {
    var undelete_button = createDOM( "input", {
      "type": "button",
      "class": "message_button",
      "value": "undelete",
      "title": "undelete note"
    } );
    var trash_link = createDOM( "a", {
      "href": "/notebooks/" + this.notebook.trash_id + "?parent_id=" + this.notebook.object_id
    }, "trash" );
    var message_div = this.display_message( "That note is in the", [ trash_link, ". ", undelete_button ], position_after )
    var self = this;
    connect( undelete_button, "onclick", function ( event ) { self.undelete_editor_via_undelete( event, result.note_id_in_trash, message_div ); } );
    return;
  }

  if ( result.note ) {
    var id = result.note.object_id;
    if ( requested_revision )
      id += " " + requested_revision;
    var actual_revision = result.note.revision;
    var actual_creation = result.note.creation;
    var note_text = result.note.contents;
    var deleted_from_id = result.note.deleted;
    var user_id = result.note.user_id;
    var username = result.note.username;
  } else {
    // if the title looks like a URL, then make it a link to an external site
    if ( /^\w+:\/\//.test( note_title ) || /^mailto:/.test( note_title ) ) {
      link.target = "_new";
      link.href = note_title;
      window.open( link.href );
      return;
    }

    var id = null;
    var note_text = "<h3>" + note_title;
    var deleted_from_id = null;
    var actual_revision = null;
    var actual_creation = null;
    var user_id = null;
    var username = null;
    this.increment_total_notes_count();
  }

  if ( requested_revision )
    var read_write = false; // show previous revisions as read-only
  else
    var read_write = this.notebook.read_write;

  var self = this;
  var editor = this.create_editor( id, note_text, deleted_from_id, actual_revision, actual_creation, read_write, true, true, position_after, user_id, username );
  if ( !requested_revision )
    connect( editor, "init_complete", function () { signal( self, "note_added", editor ); } );
  id = editor.id;

  // if a link that launched this editor was provided, update it with the created note's id
  if ( link && id )
    link.href = "/notebooks/" + this.notebook.object_id + "?note_id=" + id;
}

Wiki.prototype.create_editor = function ( id, note_text, deleted_from_id, revision, creation, read_write, highlight, focus, position_after, user_id, username ) {
  var self = this;
  var dirty = false;
  var own_notes_only = false;

  if ( read_write == NOTEBOOK_READ_ONLY )
    read_write = false;
  else if ( read_write == NOTEBOOK_READ_WRITE )
    read_write = true;
  else if ( read_write == NOTEBOOK_READ_WRITE_FOR_OWN_NOTES ) {
    own_notes_only = true;
    if ( user_id == this.user.object_id && this.user.username && this.user.username != "anonymous" )
      read_write = true;
    else
      read_write = false;
  }

  if ( isUndefinedOrNull( id ) ) {
    if ( this.notebook.read_write ) {
      id = this.next_id;
      dirty = true;
      this.invoker.invoke( "/next_id", "POST", null,
        function( result ) { self.update_next_id( result ); }
      );
    } else {
      id = 0;
    }
  }

  // for read-only notes within read-write notebooks, tack the revision timestamp onto the start of the note text
  if ( !read_write && this.notebook.read_write == NOTEBOOK_READ_WRITE && revision ) {
    var short_revision = this.brief_revision( revision );
    var note_id = id.split( ' ' )[ 0 ];
    note_text = '<p>Previous revision from ' + short_revision + '</p>' +
      '<form id="revert_form" target="/notebooks/revert_note">' +
      '<input type="hidden" name="notebook_id" value="' + this.notebook.object_id + '">' +
      '<input type="hidden" name="note_id" value="' + note_id + '">' +
      '<input type="hidden" name="revision" value="' + revision + '">' +
      '<input type="submit" class="button" value="revert to this revision" title="Roll back to this earlier version of the note.">' + 
      '</form>' + note_text;
  }

  if ( creation && note_text != "<h3></h3>" ) {
    var note_id = id.split( ' ' )[ 0 ];
    note_text = note_text + this.make_byline( username, creation, note_id );
  }

  var startup = this.startup_notes[ id ];
  var editor = new Editor( id, this.notebook.object_id, note_text, deleted_from_id, revision, read_write, startup, highlight, focus, position_after, dirty, own_notes_only );
  if ( focus )
    this.editor_focused( editor );
  else if ( !read_write )
    this.editor_focused( null );

  if ( this.notebook.read_write ) {
    connect( editor, "state_changed", this, "editor_state_changed" );
    connect( editor, "title_changed", this, "editor_title_changed" );
    connect( editor, "key_pressed", this, "editor_key_pressed" );
    connect( editor, "delete_clicked", function ( event ) { self.delete_editor( event, editor ) } );
    connect( editor, "undelete_clicked", function ( event ) { self.undelete_editor_via_trash( event, editor ) } );
    connect( editor, "changes_clicked", function ( event ) { self.toggle_editor_changes( event, editor ) } );
    connect( editor, "tools_clicked", function ( event ) { self.toggle_editor_tools( event, editor ) } );
    connect( editor, "focused", this, "editor_focused" );
    connect( editor, "mouse_hovered", function ( target ) { self.editor_mouse_hovered( editor, target ) } );
    connect( editor, "grabber_pressed", function ( event ) { self.editor_focused( null, false, false ); } );
    connect( editor, "moved", function ( editor, position_after, position_before ) {
      self.editor_moved( editor, position_after, position_before );
    } );
  }

  connect( editor, "load_editor", this, "load_editor" );
  connect( editor, "hide_clicked", function ( event ) { self.hide_editor( event, editor ) } );
  connect( editor, "submit_form", function ( form ) { self.submit_form( form ); } );
  connect( editor, "button_clicked", function ( editor, button ) { self.editor_button_clicked( editor, button ); } );

  this.clear_pulldowns();

  return editor;
}

Wiki.prototype.resize_editor = function () {
  if ( Editor.shared_iframe && Editor.shared_iframe.editor() )
    Editor.shared_iframe.editor().resize();
}

Wiki.prototype.resize_toolbar = function () {
  var last_toolbar_button = getElement( "insertOrderedList" );
  var current_toolbar_bottom = getElementPosition( last_toolbar_button ).y + getElementDimensions( last_toolbar_button ).h;
  var viewport_size = getViewportDimensions();
  var VIEWPORT_WIDTH_THRESHOLD = 1000;

  // if the toolbar is large and the bottom of the toolbar is outside of the viewport or the
  // viewport is too narrow, then make the toolbar smaller
  if ( !this.small_toolbar && ( current_toolbar_bottom > viewport_size.h || viewport_size.w < VIEWPORT_WIDTH_THRESHOLD ) ) {
    this.large_toolbar_bottom = current_toolbar_bottom;
    this.small_toolbar = true;
    this.update_toolbar();
  // otherwise, if the toolbar is small and making the toolbar large would still fit within the
  // viewport and the viewport is wide, then make the toolbar large again
  } else if ( this.small_toolbar && this.large_toolbar_bottom <= viewport_size.h && viewport_size.w >= VIEWPORT_WIDTH_THRESHOLD ) {
    if ( !this.small_toolbar ) return; // it's already big, so bail
    this.small_toolbar = false;
    this.update_toolbar();
  }
}

Wiki.prototype.detect_font_resize = function () {
  if ( !window.getComputedStyle ) return;

  var style = window.getComputedStyle( getElement( "content" ), null );
  if ( !style ) return;

  if ( style.fontSize == this.font_size )
    return;

  this.font_size = style.fontSize;
  this.resize_editor();
}

Wiki.prototype.editor_state_changed = function ( editor, link_clicked ) {
  this.update_toolbar();

  if ( !link_clicked )
    this.display_link_pulldown( editor );

  if ( editor.dirty() ) {
    var save_button = getElement( "save_button" );
    if ( save_button && save_button.disabled ) {
      save_button.disabled = false;
      save_button.value = "save";
    }
  }

  signal( this, "note_state_changed", editor );
}

Wiki.prototype.editor_title_changed = function ( editor, old_title, new_title ) {
  if ( old_title )
    delete this.open_editors[ old_title.toLowerCase() ];

  if ( new_title != null && !editor.empty() ) {
    if ( new_title )
      this.open_editors[ new_title.toLowerCase() ] = editor;
    signal( this, "note_renamed", editor, new_title );
  }
}

Wiki.prototype.display_link_pulldown = function ( editor, link, ephemeral ) {
  this.clear_messages();

  if ( !editor.read_write ) {
    this.clear_pulldowns();
    return;
  }

  if ( !link )
    link = editor.find_link_at_cursor();

  // if there's no link at the current cursor location, bail
  if ( !link ) {
    this.clear_pulldowns();
    return;
  }

  var pulldown = link.pulldown;
  var query = parse_query( link );
  var title = link_title( link, query );

  // display a Suggest_pulldown once something is typed for the link title, as long as the link
  // doesn't yet have a note_id
  if ( !pulldown && title.length > 0 && query.note_id == "new" ) {
    this.clear_pulldowns();
    var self = this;
    var suggest_pulldown = new Suggest_pulldown( this, this.notebook.object_id, this.invoker, link, editor.iframe, title, editor.document );
    connect( suggest_pulldown, "suggestion_selected", function ( note ) {
      self.update_link_with_suggestion( editor, link, note )
    } );
    return;
  }

  // if there is a link but it was just started, bail
  if ( link == editor.link_started && !pulldown ) {
    this.clear_pulldowns();
    return;
  }

  if ( pulldown ) {
    // if a Suggest_pulldown is open for the link, update the pulldown and bail
    if ( pulldown.update_suggestions ) {
      pulldown.update_suggestions( title );
      return;
    // otherwise, just update the pulldown's position
    } else {
      pulldown.update_position();
    }
  }

  var link_contains_image = getElementsByTagAndClassName( "img", null, link );

  // if the cursor is now on a link, display a link pulldown if there isn't already one open
  if ( link_title( link ).length > 0 || link_contains_image ) {
    if ( !pulldown ) {
      this.clear_pulldowns();
      // display a different pulldown depending on whether the link is a note link or a file link
      if ( link.target || !/\/files\//.test( link.href ) )
        new Link_pulldown( this, this.notebook.object_id, this.invoker, editor, link, ephemeral );
      else {
        if ( /\/files\/new$/.test( link.href ) )
          new Upload_pulldown( this, this.notebook.object_id, this.invoker, editor, link, null, ephemeral );
        else
          new File_link_pulldown( this, this.notebook.object_id, this.invoker, editor, link, ephemeral );
      }
    }
  }
}

Wiki.prototype.update_link_with_suggestion = function ( editor, link, note ) {
  link.innerHTML = note.title;

  // manually position the text cursor at the end of the link title
  editor.position_cursor_after( link );

  link.href = "/notebooks/" + this.notebook.object_id + "?note_id=" + note.object_id;

  link.pulldown.shutdown();
  link.pulldown = null;
  editor.focus();
  editor.end_link();

  this.display_link_pulldown( editor, link );
}

Wiki.prototype.editor_focused = function ( editor, synchronous, remove_empty, save_blurred ) {
  if ( remove_empty == undefined )
    remove_empty = true;
  if ( save_blurred == undefined )
    save_blurred = true;

  if ( this.focused_editor && this.focused_editor != editor ) {
    this.focused_editor.blur();
    this.clear_pulldowns();

    // if there is no focused editor anymore, release the iframe of the previously focused editor
    if ( editor == null )
      this.focused_editor.release_iframe();

    // if the formerly focused editor is completely empty, then remove it as the user leaves it and switches to this editor
    if ( this.focused_editor.empty() && remove_empty ) {
      signal( this, "note_removed", this.focused_editor.id );
      this.focused_editor.shutdown();
      this.decrement_total_notes_count();
      this.display_empty_message();
    } else if ( save_blurred ) {
      // when switching editors, save the one being left
      this.save_editor( null, null, null, synchronous );
    }
  }

  this.focused_editor = editor;
  this.update_toolbar();
}

Wiki.prototype.editor_moved = function ( editor, position_after, position_before ) {
  this.save_editor( editor, false, null, null, null, position_after, position_before );  
  if ( this.note_tree )
    this.note_tree.move_link( editor, position_after, position_before );

  // reset the revision for each open editor. this is because the server is updating the revisions
  // on the server while reordering the ntoes. and we don't want to have a stale idea of what the
  // current revision is for a given editor
  var divs = getElementsByTagAndClassName( "div", "static_note_div" );
  for ( var i in divs ) {
    var editor = divs[ i ].editor;
    editor.revision = null;
    editor.user_revisions = new Array();
  }
}

Wiki.prototype.make_byline = function ( username, creation, note_id ) {
  if ( username == "anonymous" )
    username = "admin";

  if ( username )
    var by = ' by ' + username;
  else
    var by = '';

  if ( creation )
    var timestamp = ' on ' + this.brief_revision( creation );
  else
    var timestamp = '';

  return '<div class="byline small_text">Posted' + by + timestamp +
         ' | <a href="' + window.location.pathname + '?note_id=' + note_id + '" target="_top">permalink</a>';
}

Wiki.prototype.remove_byline = function ( editor ) {
  if ( editor.document && editor.read_write ) {
    var byline = getFirstElementByTagAndClassName( "div", "byline", editor.document );
    if ( byline ) {
      removeElement( byline );
      editor.resize();
    }
  }
}

Wiki.prototype.editor_mouse_hovered = function ( editor, target ) {
  var pulldowns = getElementsByTagAndClassName( "div", "pulldown" );

  // if the mouse is hovering over a link, and no pulldowns are open, open a link pulldown
  if ( target.nodeName == "A" && pulldowns.length == 0 )
    this.display_link_pulldown( editor, target, true );
  // the mouse is hovering over something else, so clear all ephemeral pulldowns
  else
    this.clear_pulldowns( true );
}

Wiki.prototype.key_pressed = function ( event ) {
  if ( this.notebook.read_write == NOTEBOOK_READ_ONLY )
    return;

  var code = event.key().code;
  if ( event.modifier().ctrl ) {
    // ctrl-m: make a new note
    if ( code == 77 ) {
      this.create_blank_editor( event );
    // ctrl-slash: start a search
    } else if ( code == 191 ) {
      var search_text = getElement( "search_text" );
      if ( search_text )
        search_text.focus();
    // ctrl-space: save the current editor
    } else if ( code == 32 ) {
      this.save_editor();
    }
    return;
  }

  // page up: previous note
  if ( code == 33 ) {
    event.stop();
    this.focus_previous_editor();
  // page down: next note
  } else if ( code == 34 ) {
    event.stop();
    this.focus_next_editor();
  }
}

Wiki.prototype.editor_key_pressed = function ( editor, event ) {
  this.remove_byline( editor );

  var code = event.key().code;

  if ( event.modifier().ctrl ) {
    // ctrl-backtick: message with frame HTML contents (for debugging)
    if ( code == 192 || code == 96 ) {
      this.display_message( editor.contents() );
      event.stop();
    // ctrl-b: bold
    } else if ( code == 66 ) {
      this.toggle_button( event, "bold" );
    // ctrl-i: italic
    } else if ( code == 73 ) {
      this.toggle_button( event, "italic" );
    // ctrl-u: underline
    } else if ( code == 85 ) {
      this.toggle_button( event, "underline" );
    // ctrl-s: strikethrough
    } else if ( code == 83 ) {
      this.toggle_button( event, "strikethrough" );
    // ctrl-period: unordered list
    } else if ( code == 190 ) {
      this.toggle_button( event, "insertUnorderedList" );
    // ctrl-1: ordered list
    } else if ( code == 49 ) {
      this.toggle_button( event, "insertOrderedList" );
    // ctrl-l: link
    } else if ( code == 76 ) {
      this.toggle_link_button( event );
    // ctrl-m: make a new note
    } else if ( code == 77 ) {
      this.create_blank_editor( event );
    // ctrl-h: hide note
    } else if ( code == 72 ) {
      if ( !editor.deleted_from_id )
        this.hide_editor( event );
    // ctrl-d: delete note
    } else if ( code == 68 ) {
      this.delete_editor( event );
    // ctrl-slash: start a search
    } else if ( code == 191 ) {
      var search_text = getElement( "search_text" );
      if ( search_text )
        search_text.focus();
    // ctrl-space: save the current editor
    } else if ( code == 32 ) {
      this.save_editor();
    }
  // shift-tab: outdent
  } else if ( event.modifier().shift && code == 9 ) {
    // ignore shift-tab here if a Suggest_pulldown is open
    var link = editor.find_link_at_cursor();
    if ( link && link.pulldown && link.pulldown.visible && link.pulldown.visible() )
      return;

    editor.exec_command( "outdent" );
    event.stop();
  // tab: outdent
  } else if ( code == 9 ) {
    // ignore tab here if a Suggest_pulldown is open
    var link = editor.find_link_at_cursor();
    if ( link && link.pulldown && link.pulldown.visible && link.pulldown.visible() )
      return;
    
    editor.exec_command( "indent" );
    event.stop();
  // page up: previous note
  } else if ( code == 33 ) {
    event.stop();
    this.focus_previous_editor();
  // page down: next note
  } else if ( code == 34 ) {
    event.stop();
    this.focus_next_editor();
  // IE: hitting space while making a link shouldn't end the link
  } else if ( code == 32 && editor.document.selection && editor.state_enabled( "a" ) ) {
    var range = editor.document.selection.createRange();
    range.text = " ";
    event.stop();
  // IE: hitting backspace while making a link shouldn't end the link
  } else if ( code == 8 && editor.document.selection ) {
    var range = editor.document.selection.createRange();
    range.moveStart( "character", -1 );
    if ( range.text != "" ) {
      range.text = "";
      event.stop();
    }
  }
}

Wiki.prototype.focus_previous_editor = function () {
  if ( !this.focused_editor ) {
    var div = getFirstElementByTagAndClassName( "div", "static_note_div" );
    if ( !div || !div.editor ) return;
    div.editor.highlight();
    return;
  }

  var previous_editor = this.focused_editor.previous_editor();
  if ( !previous_editor ) return;

  this.editor_focused( null );
  previous_editor.highlight();
}

Wiki.prototype.focus_next_editor = function () {
  if ( !this.focused_editor ) {
    var div = getFirstElementByTagAndClassName( "div", "static_note_div" );
    if ( !div || !div.editor ) return;
    div.editor.highlight();
    return;
  }

  var next_editor = this.focused_editor.next_editor();
  if ( !next_editor ) return;

  this.editor_focused( null );
  next_editor.highlight();
}

Wiki.prototype.get_toolbar_image_dir = function ( always_small ) {
  var toolbar_image_dir = IMAGE_DIR + "toolbar/";
  if ( always_small || this.small_toolbar )
    toolbar_image_dir += "small/";

  return toolbar_image_dir;
}

Wiki.prototype.resize_toolbar_button = function ( button ) {
  var SMALL_BUTTON_SIZE = 20;
  var LARGE_BUTTON_SIZE = 40;

  var button_size = getElementDimensions( button );
  
  if ( this.small_toolbar || button.always_small ) {
    if ( button_size.w == SMALL_BUTTON_SIZE ) return false;
    setElementDimensions( button, { "w": SMALL_BUTTON_SIZE, "h": SMALL_BUTTON_SIZE } );
  } else {
    if ( button_size.w == LARGE_BUTTON_SIZE ) return false;
    setElementDimensions( button, { "w": LARGE_BUTTON_SIZE, "h": LARGE_BUTTON_SIZE } );
  }

  return true;
}

Wiki.prototype.make_image_button = function ( name, filename_prefix, always_small ) {
  var button = getElement( name );
  var toolbar_image_dir = this.get_toolbar_image_dir( always_small );

  if ( !filename_prefix )
    filename_prefix = name;

  button.name = name;
  button.filename_prefix = filename_prefix;
  button.always_small = always_small;

  this.resize_toolbar_button( button );
  this.connect_image_button( button );
}

Wiki.prototype.connect_image_button = function ( button, filename_prefix ) {
  var self = this;

  connect( button, "onmouseover", function ( event ) {
    var toolbar_image_dir = self.get_toolbar_image_dir( button.always_small );
    if ( /_down/.test( button.src ) )
      button.src = toolbar_image_dir + button.filename_prefix + "_button_down_hover.png";
    else
      button.src = toolbar_image_dir + button.filename_prefix + "_button_hover.png";
  } );

  connect( button, "onmouseout", function ( event ) {
    var toolbar_image_dir = self.get_toolbar_image_dir( button.always_small );
    if ( /_down/.test( button.src ) )
      button.src = toolbar_image_dir + button.filename_prefix + "_button_down.png";
    else
      button.src = toolbar_image_dir + button.filename_prefix + "_button.png";
  } );

  if ( button.name == "newNote" || button.name == "new_notebook" || button.name == "new_note_tree_link" ) {
    connect( button, "onmousedown", function ( event ) {
      var toolbar_image_dir = self.get_toolbar_image_dir( button.always_small );
      if ( /_hover/.test( button.src ) )
        button.src = toolbar_image_dir + button.filename_prefix + "_button_down_hover.png";
      else
        button.src = toolbar_image_dir + button.filename_prefix + "_button_down.png";
    } );
    connect( button, "onmouseup", function ( event ) {
      var toolbar_image_dir = self.get_toolbar_image_dir( button.always_small );
      if ( /_hover/.test( button.src ) )
        button.src = toolbar_image_dir + button.filename_prefix + "_button_hover.png";
      else
        button.src = toolbar_image_dir + button.filename_prefix + "_button.png";
    } );
  }
}

Wiki.prototype.down_image_button = function ( name ) {
  var button = getElement( name );
  if ( !button || !button.filename_preifx )
    return;

  var toolbar_image_dir = this.get_toolbar_image_dir( button.always_small );

  if ( !this.resize_toolbar_button( button ) && /_down/.test( button.src ) )
    return;

  if ( /_hover/.test( button.src ) )
    button.src = toolbar_image_dir + button.filename_prefix + "_button_down_hover.png";
  else
    button.src = toolbar_image_dir + button.filename_prefix + "_button_down.png";
}

Wiki.prototype.up_image_button = function ( name ) {
  var button = getElement( name );
  if ( !button || !button.filename_prefix )
    return;

  var toolbar_image_dir = this.get_toolbar_image_dir( button.always_small );

  if ( !this.resize_toolbar_button( button ) && !/_down/.test( button.src ) )
    return;

  if ( /_hover/.test( button.src ) )
    button.src = toolbar_image_dir + button.filename_prefix + "_button_hover.png";
  else
    button.src = toolbar_image_dir + button.filename_prefix + "_button.png";
}

Wiki.prototype.toggle_image_button = function ( name ) {
  var button = getElement( name );
  if ( !button || !button.filename_prefix )
    return;

  var toolbar_image_dir = this.get_toolbar_image_dir( button.always_small );

  if ( /_down/.test( button.src ) ) {
    if ( /_hover/.test( button.src ) )
      button.src = toolbar_image_dir + button.filename_prefix + "_button_hover.png";
    else
      button.src = toolbar_image_dir + button.filename_prefix + "_button.png";
    this.resize_toolbar_button( button );
    return false;
  } else {
    if ( /_hover/.test( button.src ) )
      button.src = toolbar_image_dir + button.filename_prefix + "_button_down_hover.png";
    else
      button.src = toolbar_image_dir + button.filename_prefix + "_button_down.png";
    this.resize_toolbar_button( button );
    return true;
  }
}

Wiki.prototype.toggle_button = function ( event, button_id ) {
  this.clear_messages();
  this.clear_pulldowns();

  if ( this.focused_editor && this.focused_editor.read_write ) {
    this.focused_editor.focus();
    if ( button_id == "title" )
      this.focused_editor.exec_command( "h3" );
    else
      this.focused_editor.exec_command( button_id );
    this.focused_editor.resize();
    this.toggle_image_button( button_id );
  }

  event.stop();
}

Wiki.prototype.update_button = function ( button_id, state_name, node_names ) {
  if ( state_name && node_names && this.focused_editor.state_enabled( state_name, node_names ) )
    this.down_image_button( button_id );
  else
    this.up_image_button( button_id );
}

Wiki.prototype.update_toolbar = function() {
  var node_names = null;
  var link = null;

  // a read-only notebook doesn't have a visible toolbar
  if ( this.notebook.read_write == NOTEBOOK_READ_ONLY )
    return;

  if ( this.focused_editor ) {
    node_names = this.focused_editor.current_node_names();
    link = this.focused_editor.find_link_at_cursor();
  }

  this.update_button( "newNote" );
  this.update_button( "bold", "b", node_names );
  this.update_button( "italic", "i", node_names );
  this.update_button( "underline", "u", node_names );
  this.update_button( "strikethrough", "strike", node_names );
  this.update_button( "font", "font", node_names );
  this.update_button( "title", "h3", node_names );
  this.update_button( "insertUnorderedList", "ul", node_names );
  this.update_button( "insertOrderedList", "ol", node_names );

  if ( link ) {
    // determine whether the link is a note link or a file link
    if ( link.target || !/\/files\//.test( link.href ) ) {
      this.down_image_button( "createLink" );
      this.up_image_button( "attachFile" );
    } else {
      this.up_image_button( "createLink" );
      this.down_image_button( "attachFile" );
    }
  } else {
    this.up_image_button( "createLink" );
    this.up_image_button( "attachFile" );
  }
}

Wiki.prototype.toggle_link_button = function ( event ) {
  this.clear_messages();
  this.clear_pulldowns();
  var link = null;

  if ( this.focused_editor && this.focused_editor.read_write ) {
    this.focused_editor.focus();
    if ( this.toggle_image_button( "createLink" ) )
      link = this.focused_editor.start_link();
    else
      link = this.focused_editor.end_link();

    if ( link && link.parentNode != null ) {
      var self = this;
      this.resolve_link( link_title( link ), link, false, function ( summary ) {
        self.display_link_pulldown( self.focused_editor, link );
      } );
    } else {
      this.display_link_pulldown( this.focused_editor );
    }
  }

  event.stop();
}

Wiki.prototype.toggle_attach_button = function ( event ) {
  if ( this.focused_editor && this.focused_editor.read_write ) {
    this.focused_editor.focus();
    if ( this.toggle_image_button( "attachFile" ) )
      var link = this.focused_editor.start_file_link();
    else
      var link = this.focused_editor.end_link();

    // if a pulldown is already open, then just close it
    var pulldown_id = "upload_" + this.focused_editor.id;
    var existing_div = getElement( pulldown_id );
    if ( !existing_div ) {
      pulldown_id = "file_link_" + this.focused_editor.id;
      existing_div = getElement( pulldown_id );
    }

    if ( existing_div ) {
      existing_div.pulldown.shutdown();
      existing_div.pulldown = null;
      return;
    }

    this.clear_messages();
    this.clear_pulldowns();

    new Upload_pulldown( this, this.notebook.object_id, this.invoker, this.focused_editor, link, null );
  }

  event.stop();
}

Wiki.prototype.toggle_font_button = function ( event ) {
  if ( this.focused_editor && this.focused_editor.read_write ) {
    this.focused_editor.focus();

    // if a pulldown is already open, then just close it
    var existing_div = getElement( "font_pulldown" );

    if ( existing_div ) {
      this.up_image_button( "font" );
      existing_div.pulldown.shutdown();
      existing_div.pulldown = null;
      return;
    }

    this.down_image_button( "font" );
    this.clear_messages();
    this.clear_pulldowns();

    new Font_pulldown( this, this.notebook.object_id, this.invoker, event.target(), this.focused_editor );
  }

  event.stop();
}

Wiki.prototype.hide_editor = function ( event, editor ) {
  this.clear_messages();
  this.clear_pulldowns();

  if ( this.focused_editor )
    this.editor_focused( null, false, true, false );

  if ( !editor ) {
    editor = this.focused_editor;
    this.focused_editor = null;
  }

  if ( editor ) {
    var id = editor.id;

    // if the editor to hide is completely empty, then simply remove it
    if ( editor.empty() ) {
      signal( this, "note_removed", editor.id );
      editor.shutdown();
      this.decrement_total_notes_count();
      this.display_empty_message();
    } else {
      // before hiding an editor, save it
      if ( this.notebook.read_write != NOTEBOOK_READ_ONLY && editor.read_write ) {
        var self = this;
        this.save_editor( editor, false, function () {
          editor.shutdown();
          self.display_empty_message();
        } );
      } else {
        editor.shutdown();
        this.display_empty_message();
      }
    }
  }

  event.stop();
}

Wiki.prototype.delete_editor = function ( event, editor ) {
  this.clear_messages();
  this.clear_pulldowns();

  if ( this.focused_editor )
    this.editor_focused( null, false, true, false );

  if ( !editor ) {
    editor = this.focused_editor;
    this.focused_editor = null;
  }

  if ( !editor ) {
    event.stop();
    return;
  }

  if ( this.startup_notes[ editor.id ] )
    delete this.startup_notes[ editor.id ];

  var self = this;
  this.save_editor( editor, false, function () {
    if ( self.notebook.read_write != NOTEBOOK_READ_ONLY && editor.read_write ) {
      self.invoker.invoke( "/notebooks/delete_note", "POST", { 
        "notebook_id": self.notebook.object_id,
        "note_id": editor.id
      }, function ( result ) { self.display_storage_usage( result.storage_bytes ); } );
    }

    if ( editor == self.focused_editor )
      self.focused_editor = null;

    if ( self.notebook.trash_id && !editor.empty() ) {
      var undo_button = createDOM( "input", {
        "type": "button",
        "class": "message_button",
        "value": "undo",
        "title": "undo deletion"
      } );
      var trash_link = createDOM( "a", {
        "href": "/notebooks/" + self.notebook.trash_id + "?parent_id=" + self.notebook.object_id
      }, "trash" );
      var message_div = self.display_message( "The note has been moved to the", [ trash_link, ". ", undo_button ], editor.holder );
      connect( undo_button, "onclick", function ( event ) { self.undelete_editor_via_undo( event, editor, message_div ); } );
    }

    signal( self, "note_removed", editor.id );

    editor.shutdown();
    self.decrement_total_notes_count();
    self.display_empty_message();
  }, false, true );

  event.stop();
}

Wiki.prototype.undelete_editor_via_trash = function ( event, editor ) {
  this.clear_messages();
  this.clear_pulldowns();

  if ( !editor ) {
    editor = this.focused_editor;
    this.focused_editor = null;
  }

  if ( editor ) {
    if ( this.startup_notes[ editor.id ] )
      delete this.startup_notes[ editor.id ];

    if ( this.notebook.read_write != NOTEBOOK_READ_ONLY && editor.read_write ) {
      var self = this;
      this.invoker.invoke( "/notebooks/undelete_note", "POST", { 
        "notebook_id": editor.deleted_from_id,
        "note_id": editor.id
      }, function ( result ) { self.display_storage_usage( result.storage_bytes ); } );
    }

    if ( editor == this.focused_editor )
      this.focused_editor = null;

    signal( this, "note_removed", editor.id );

    editor.shutdown();
    this.decrement_total_notes_count();
    this.display_empty_message();
  }

  event.stop();
}

Wiki.prototype.undelete_editor_via_undo = function( event, editor, position_after ) {
  if ( editor ) {
    if ( this.notebook.read_write != NOTEBOOK_READ_ONLY && editor.read_write ) {
      var self = this;
      this.invoker.invoke( "/notebooks/undelete_note", "POST", { 
        "notebook_id": this.notebook.object_id,
        "note_id": editor.id
      }, function ( result ) {
        self.display_storage_usage( result.storage_bytes );
        self.clear_messages();
        self.clear_pulldowns();
        self.startup_notes[ editor.id ] = true;
        self.increment_total_notes_count();
        self.load_editor( "Note not found.", editor.id, null, null, null, position_after );
      } );
    }
  }

  event.stop();
}

Wiki.prototype.undelete_editor_via_undelete = function( event, note_id, position_after ) {
  if ( this.notebook.read_write != NOTEBOOK_READ_ONLY ) {
    var self = this;
    this.invoker.invoke( "/notebooks/undelete_note", "POST", { 
      "notebook_id": this.notebook.object_id,
      "note_id": note_id
    }, function ( result ) {
      self.display_storage_usage( result.storage_bytes );
      self.clear_messages();
      self.clear_pulldowns();
      self.startup_notes[ note_id ] = true;
      self.increment_total_notes_count();
      self.load_editor( "Note not found.", note_id, null, null, null, position_after );
    } );
  }

  event.stop();
}

Wiki.prototype.undelete_notebook = function( event, notebook_id ) {
  this.invoker.invoke( "/notebooks/undelete", "POST", { 
    "notebook_id": notebook_id
  } );

  event.stop();
}

Wiki.prototype.compare_versions = function( event, editor, previous_revision ) {
  this.clear_pulldowns();

  // display a diff between the two revisions for examination by the user
  this.load_editor( editor.title, editor.id, editor.revision, previous_revision, editor.closed ? null : editor.holder );
}

Wiki.prototype.save_editor = function ( editor, fire_and_forget, callback, synchronous, suppress_save_signal, position_after, position_before ) {
  if ( !editor )
    editor = this.focused_editor;

  var self = this;
  if ( editor && editor.read_write && !editor.closed &&
       ( ( !editor.empty() && editor.dirty() ) || position_after || position_before ) ) {
    editor.scrape_title();
    this.remove_byline( editor );

    this.invoker.invoke( "/notebooks/save_note", "POST", { 
      "notebook_id": this.notebook.object_id,
      "note_id": editor.id,
      "contents": editor.contents(),
      "startup": editor.startup,
      "previous_revision": editor.revision ? editor.revision : "None",
      "position_after": position_after ? position_after.id : "None",
      "position_before": position_before ? position_before.id : "None"
    }, function ( result ) {
      self.update_editor_revisions( result, editor );
      self.display_storage_usage( result.storage_bytes );
      editor.mark_clean();

      var save_button = getElement( "save_button" );
      if ( save_button && self.focused_editor && !self.focused_editor.dirty() ) {
        save_button.disabled = true;
        save_button.value = "saved";
      }

      if ( editor.startup )
        self.startup_notes[ editor.id ] = true;
      else if ( self.startup_notes[ editor.id ] )
        delete self.startup_notes[ editor.id ];

      // special case to rename a forum notebook when its first note is renamed
      if ( result.rank == 0 && self.notebook_has_tag( self.notebook, "forum" ) )
        self.end_notebook_rename( editor.title, true );

      if ( callback )
        callback();
      if ( !suppress_save_signal )
        signal( self, "note_saved", editor );
    }, null, synchronous, fire_and_forget );
  } else {
    var save_button = getElement( "save_button" );
    if ( save_button && this.focused_editor && !this.focused_editor.dirty() ) {
      save_button.disabled = true;
      save_button.value = "saved";
    }

    if ( callback )
      callback();
  }
}

Wiki.prototype.update_editor_revisions = function ( result, editor ) {
  // if there's not a newly saved revision, then the contents are unchanged, so bail
  if ( !result.new_revision )
    return;

  var client_previous_revision = editor.revision;
  editor.revision = result.new_revision.revision;

  // if the server's idea of the previous revision doesn't match the client's, then someone has
  // gone behind our back and saved the editor's note from another window
  if ( result.previous_revision && client_previous_revision &&
       result.previous_revision.revision != client_previous_revision ) {
    var compare_button = createDOM( "input", {
      "type": "button",
      "class": "message_button",
      "value": "compare versions",
      "title": "compare your version with the modified version"
    } );
    this.display_error(
      'Your changes to the note titled "' + editor.title +
      '" have overwritten changes made in another window by ' + ( result.previous_revision.username || 'you' ) + '.',
      [ compare_button ], editor.holder
    );

    var self = this;
    connect( compare_button, "onclick", function ( event ) {
      self.compare_versions( event, editor, result.previous_revision.revision );
    } );

    if ( !editor.user_revisions || editor.user_revisions.length == 0 )
      return;
    editor.user_revisions.push( result.previous_revision );
  }

  // add the new revision to the editor's revisions list
  if ( !editor.user_revisions || editor.user_revisions.length == 0 )
    return;
  editor.user_revisions.push( result.new_revision );
}

Wiki.prototype.submit_form = function ( form ) {
  this.clear_messages();
  this.clear_pulldowns();

  var self = this;
  var args = {}
  var url = form.getAttribute( "target" );
  var callback = null;

  if ( url == "/users/signup" ) {
    args[ "invite_id" ] = this.invite_id;
    args[ "rate_plan" ] = this.signup_plan;
    args[ "yearly" ] = this.yearly;
  } else if ( url == "/users/login" ) {
    args[ "invite_id" ] = this.invite_id;
    args[ "after_login" ] = this.after_login;
  } else if ( url == "/users/send_invites" ) {
    callback = function ( result ) {
      if ( !result.invites ) return;
      self.invites = result.invites;
      self.share_notebook();
    }
  } else if ( url == "/users/update_settings" ) {
    callback = function ( result ) {
      self.user.email_address = result.email_address || "";
      self.display_message( "Your account settings have been updated." );
    }
  } else if ( url == "/users/signup_group_member" ) {
    callback = function ( result ) {
      var group_id = getFirstElementByTagAndClassName( "input", "group_id", form ).value;
      self.invoker.invoke( "/groups/load_users", "GET", {
        "group_id": group_id
      }, function ( result ) {
        self.display_group_settings( result );
      } );
    }
  } else if ( url == "/notebooks/revert_note" ) {
    callback = function ( result ) {
      var editor = editor_by_id( form.note_id.value );

      if ( editor ) {
        self.update_editor_revisions( result, editor );
        editor.mark_clean();

        if ( result.new_revision ) {
          if ( editor.document && editor.document.body )
            editor.document.body.innerHTML = result.contents;
          else if ( editor.div )
            editor.div.innerHTML = result.contents;

          editor.resize();
          editor.scrape_title();
        }

        editor.highlight();

        signal( self, "note_saved", editor );
      }

      if ( result.new_revision )
        self.display_message( "The note has been reverted to an earlier revision.", [],
                               editor && editor.holder || null );
      else
        self.display_message( "The note is already at that revision.", [],
                              editor && editor.holder || null );

      self.display_storage_usage( result.storage_bytes );
    }
  }

  this.invoker.invoke( url, "POST", args, callback, form );
}

Wiki.prototype.editor_button_clicked = function ( editor, button ) {
  this.clear_messages();
  this.clear_pulldowns();

  var self = this;

  if ( hasElementClass( button, "revoke_button" ) ) {
    var invite_id = button.id.split( "_" ).pop();

    this.invoker.invoke( "/users/revoke_invite", "POST", {
      "notebook_id": this.notebook.object_id,
      "invite_id": invite_id
    }, function ( result ) {
      if ( !result.invites ) return;
      self.invites = result.invites;
      self.share_notebook();
    } );
  } else if ( hasElementClass( button, "admin_button" ) ) {
    var group_id = button.id.split( "_" ).pop();

    this.invoker.invoke( "/groups/load_users", "GET", {
      "group_id": group_id
    }, function ( result ) {
      self.display_group_settings( result );
    } );
  } else if ( hasElementClass( button, "remove_user_button" ) ) {
    var id_pieces = button.id.split( "_" );
    var group_id = id_pieces.pop();
    var user_id = id_pieces.pop();

    this.invoker.invoke( "/users/remove_group", "POST", {
      "user_id_to_remove": user_id,
      "group_id": group_id
    }, function ( result ) {
      self.invoker.invoke( "/groups/load_users", "GET", {
        "group_id": group_id
      }, function ( result ) {
        self.display_group_settings( result );
      } );
    } );
  }
}

Wiki.prototype.search = function ( event ) {
  this.clear_messages();
  this.clear_pulldowns();

  var self = this;
  this.invoker.invoke( "/notebooks/search", "GET", {
      "notebook_id": this.notebook.object_id
    },
    function( result ) { self.display_search_results( result ); },
    "search_form"
  );

  event.stop();
}

Wiki.prototype.search_focused = function ( event ) {
  var search_text = getElement( "search_text" );

  if ( search_text.value == 'search' )
    search_text.value = '';
}

Wiki.prototype.search_blurred = function ( event ) {
  var search_text = getElement( "search_text" );

  if ( search_text.value == '' )
    search_text.value = 'search';
}

Wiki.prototype.search_key_released = function ( event ) {
  var search_text = getElement( "search_text" );
  var self = this;

  if ( search_text.pulldown ) {
    search_text.pulldown.update_suggestions( search_text.value );
  } else if ( event.key().code != 13 ) {
    search_text.pulldown = new Suggest_pulldown( this.wiki, this.notebook.object_id, this.invoker, search_text, null, search_text.value, search_text );
    connect( search_text.pulldown, "suggestion_selected", function ( note ) {
      self.load_search_suggestion( note )
    } );
  }
}

Wiki.prototype.load_search_suggestion = function ( note ) {
  var search_text = getElement( "search_text" );
  search_text.value = note.title;

  this.load_editor( note.title, note.object_id );

  if ( search_text.pulldown ) {
    search_text.pulldown.shutdown();
    search_text.pulldown = null;
  }
}

Wiki.prototype.notebook_has_tag = function ( notebook, tag_name, tag_value ) {
  // determine whether the given notebook has a tag with tag_name, and (optionally) tag_value
  for ( var i in notebook.tags ) {
    var tag = notebook.tags[ i ];

    if ( tag.name == tag_name ) {
      if ( tag_value && tag.value != tag_value )
        return false;
      return true;
    }
  }

  return false;
}

Wiki.prototype.display_search_results = function ( result ) {
  // if there are no search results, indicate that and bail
  if ( !result || result.notes.length == 0 ) {
    if ( this.search_results_editor )
      this.search_results_editor.shutdown();
    this.display_message( "No matching notes.", undefined, getElement( "notes_top" ) );
    return;
  }

  // create a "magic" search results note
  if ( this.notebook_has_tag( this.notebook, "forum" ) )
    var notebook_word = "discussion";
  else
    var notebook_word = "notebook";

  var list = createDOM( "span", {} );
  var other_notebooks_section = false;

  for ( var i in result.notes ) {
    var note = result.notes[ i ]
    if ( !note.title ) continue;

    if ( note.contents.length == 0 ) {
      var summary = "empty note";
    } else {
      var summary = note.summary;

      // if the summary appears not to end with a complete sentence, add "..."
      if ( !/[?!.]\s*$/.test( summary ) )
        summary = summary + " <b>...</b>";
    }

    var summary_span = createDOM( "span" );
    summary_span.setAttribute( "class", "search_results_summary" );
    summary_span.innerHTML = summary;

    // when a link is clicked for a note from a notebook other than the current one, open it in a
    // new window
    var link_attributes = { "href": "/notebooks/" + note.notebook_id + "?note_id=" + note.object_id };
    if ( note.notebook_id != this.notebook.object_id ) {
      link_attributes[ "target" ] = "_new";

      if ( !other_notebooks_section ) {
        other_notebooks_section = true;
        if ( i == 0 )
          appendChildNodes( list, createDOM( "p", {}, "No matching notes in this " + notebook_word + "." ) );

        appendChildNodes( list, createDOM( "hr" ), createDOM( "h4", {}, "other " + notebook_word + "s" ) );
      }
    }

    var notebook = this.notebooks_by_id[ note.notebook_id ];

    appendChildNodes( list,
      createDOM( "p", {},
        createDOM( "a", link_attributes, note.title ),
        other_notebooks_section && notebook && createDOM( "span", { "class": "small_text" }, " (", notebook.name, ")" ) || null,
        createDOM( "br" ),
        summary_span
      )
    );
  }

  this.search_results_editor = this.create_editor( "search_results", "<h3>search results</h3>" + list.innerHTML, undefined, undefined, undefined, false, true, false, getElement( "notes_top" ) );
}

Wiki.prototype.share_notebook = function () {
  this.clear_pulldowns();

  var share_notebook_frame = getElement( "note_share_notebook" );
  if ( share_notebook_frame )
    share_notebook_frame.editor.shutdown();

  var collaborators_label = createDOM( "label",
    { "for": "collaborators_radio", "class": "radio_label", "title": "Collaborators may view and edit this notebook." },
    "collaborators"
  );
  var viewers_label = createDOM( "label",
    { "for": "viewers_radio", "class": "radio_label", "title": "Viewers may only view this notebook." },
    "viewers"
  );
  var owners_label = createDOM( "label",
    { "for": "owners_radio", "class": "radio_label", "title": "Owners may view, edit, rename, delete, and invite people to this notebook." },
    "owners"
  );

  var collaborators_radio = createDOM( "input",
    { "type": "radio", "id": "collaborators_radio", "name": "access", "value": "collaborator", "checked": "true" }
  );
  var viewers_radio = createDOM( "input",
    { "type": "radio", "id": "viewers_radio", "name": "access", "value": "viewer" }
  );
  var owners_radio = createDOM( "input",
    { "type": "radio", "id": "owners_radio", "name": "access", "value": "owner" }
  )

  if ( this.rate_plan.notebook_collaboration ) {
    var access_area = createDOM( "p", { "id": "access_choices" },
      createDOM( "p", {}, "Invite these people as:" ),
      createDOM( "table" , { "id": "access_table", "class": "radio_table" },
        createDOM( "tr", {},
          createDOM( "td", {}, collaborators_radio, collaborators_label ),
          createDOM( "td", {}, viewers_radio, viewers_label ),
          createDOM( "td", {}, owners_radio, owners_label )
        )
      )
    );
  } else {
    var access_area = createDOM( "p", {},
      createDOM( "b", {}, "Note: " ),
      "These people will only be able to ", createDOM( "i", "view" ), " your notebook. ",
      "If you'd like them to be able to ", createDOM( "i", "edit" ),
      " your notebook as well, please ",
      createDOM( "a", { "href": "/upgrade", "target": "_new" }, "upgrade" ),
      " your account.",
      createDOM( "input", { "type": "hidden", "name": "access", "value": "viewer" } )
    );
  }

  var invite_area = createDOM( "p", { "id": "invite_area" } );
  this.display_invites( invite_area );

  var div = createDOM( "div", {}, 
    createDOM( "form", { "id": "invite_form", "target": "/users/send_invites" },
      createDOM( "input", { "type": "hidden", "name": "notebook_id", "value": this.notebook.object_id } ),
      createDOM( "p", {},
        createDOM( "b", {}, "people to invite" ),
        createDOM( "br", {} ),
        createDOM( "textarea",
          { "name": "email_addresses", "class": "textarea_field", "cols": "40", "rows": "4", "wrap": "off" }
        )
      ),
      createDOM( "p", {}, "Please separate email addresses with commas, spaces, or the enter key." ),
      access_area,
      createDOM( "p", {},
        createDOM( "input",
          { "type": "submit", "name": "invite_button", "id": "invite_button", "class": "button", "value": "send invites" }
        )
      ),
      invite_area
    ),
    createDOM( "div", {},
      createDOM(
        "a", { "href": "/notebooks/" + this.notebook.object_id + "?preview=viewer", "target": "_new" },
        "Preview this notebook as a viewer."
      )
    ),
    this.rate_plan.notebook_collaboration ? createDOM( "div", {},
      createDOM(
        "a", { "href": "/notebooks/" + this.notebook.object_id + "?preview=collaborator", "target": "_new" },
        "Preview this notebook as a collaborator."
      )
    ) : null
  );

  this.create_editor( "share_notebook", "<h3>share this notebook</h3>" + div.innerHTML, undefined, undefined, undefined, false, true, false, getElement( "notes_top" ) );
}

Wiki.prototype.display_invites = function ( invite_area ) {
  if ( !this.invites || this.invites.length == 0 )
    return;

  var collaborators = createDOM( "div", { "id": "collaborators" } );
  var viewers = createDOM( "div", { "id": "viewers" } );
  var owners = createDOM( "div", { "id": "owners" } );
  var self = this;

  var addresses = new Array();

  for ( var i in this.invites ) {
    var invite = this.invites[ i ];

    // if there are multiple invites for a given email address, only display those that are
    // redeemed
    if ( addresses[ invite.email_address ] == true && !invite.redeemed_user_id )
      continue;

    var revoke_button = createDOM( "input", {
      "type": "button",
      "id": "revoke_" + invite.object_id,
      "class": "revoke_button button",
      "value": " x ",
      "title": "revoke this person's notebook access"
    } );

    var add_invite_to = null;
    if ( invite.owner ) {
      add_invite_to = owners;
    } else {
      if ( invite.read_write )
        add_invite_to = collaborators;
      else
        add_invite_to = viewers;
    }

    appendChildNodes(
      add_invite_to, createDOM( "div", { "class": "invite indented" },
        invite.email_address, " ",
        createDOM( "span", { "class": "invite_status" },
          invite.redeemed_username ? "(invite accepted by " + invite.redeemed_username + ")" : "(waiting for invite to be accepted)"
        ),
        " ", revoke_button,
        !invite.redeemed_username && createDOM( "span", {},
          createDOM( "br" ),
          createDOM( "span", { "class": "invite_link_area" },
            "invite link: " + location.protocol + "//" + location.host + "/i/" + invite.object_id
          )
        ) || ""
      )
    );

    addresses[ invite.email_address ] = true;
  }

  var div = createDOM( "div" );

  if ( collaborators.childNodes.length > 0 ) {
    var p = createDOM( "p" );
    appendChildNodes( p, createDOM( "b", {}, "collaborators" ) );
    appendChildNodes( p, collaborators );
    appendChildNodes( div, p );
  }
  if ( viewers.childNodes.length > 0 ) {
    var p = createDOM( "p" );
    appendChildNodes( p, createDOM( "b", {}, "viewers" ) );
    appendChildNodes( p, viewers );
    appendChildNodes( div, p );
  }
  if ( owners.childNodes.length > 0 ) {
    var p = createDOM( "p" );
    appendChildNodes( p, createDOM( "b", {}, "owners" ) );
    appendChildNodes( p, owners );
    appendChildNodes( div, p );
  }

  replaceChildNodes( invite_area, div );
}

Wiki.prototype.display_settings = function () {
  this.clear_pulldowns();

  var settings_frame = getElement( "note_settings" );
  if ( settings_frame ) {
    settings_frame.editor.highlight();
    return;
  }

  var group_list = createDOM( "div" );

  var div = createDOM( "div", {}, 
    createDOM( "form", { "id": "settings_form", "target": "/users/update_settings" },
      createDOM( "p", {},
        createDOM( "b", {}, "email address" ),
        createDOM( "br", {} ),
        createDOM( "input",
          { "type": "text", "name": "email_address", "id": "email_address", "class": "text_field",
            "size": "30", "maxlength": "60", "value": this.user.email_address || "" }
        )
      ),
      createDOM( "p", {},
        createDOM( "input",
          { "type": "submit", "name": "settings_button", "id": "settings_button", "class": "button", "value": "save settings" }
        )
      ),
      createDOM( "p", { "class": "small_text" },
        "Your email address will ",
        createDOM( "a", { "href": "/privacy", "target": "_new" }, "never be shared" ),
        ". It will only be used for password resets, contacting you about account problems, and the from address in any invite emails you send."
      )
    ),
    createDOM( "p", {},
      createDOM( "b", {}, "group membership" ),
      createDOM( "br", {} ),
      group_list
    ),
    createDOM( "p", {},
      createDOM(
        "a", { "href": "/pricing", "target": "_top" },
        "Upgrade, downgrade, or cancel your account."
      )
    )
  );

  for ( var i in this.groups ) {
    var group = this.groups[ i ];
    var item = createDOM( "div", { "class": "indented" } );
    appendChildNodes( group_list, item );
    appendChildNodes( item, group.name );

    if ( group.admin ) {
      appendChildNodes( item, createDOM( "input", {
        "id": "admin_" + group.object_id,
        "class": "admin_button button",
        "type": "button",
        "value": "admin",
        "title": "administer this group's users"
      } ) );
    }
  }

  if ( this.groups.length == 0 ) {
    var item = createDOM( "div", { "class": "indented" }, "You're not a member of any groups." );
    appendChildNodes( group_list, item );
  }

  this.create_editor( "settings", "<h3>account settings</h3>" + div.innerHTML, undefined, undefined, undefined, false, true, false, getElement( "notes_top" ) );
}

Wiki.prototype.display_group_settings = function ( result ) {
  this.clear_pulldowns();

  var group_frame = getElement( "note_group_" + result.group.object_id );
  if ( group_frame )
    group_frame.editor.shutdown();

  var admin_list = createDOM( "div" );
  var user_list = createDOM( "div" );

  var div = createDOM( "div", {}, 
    createDOM( "form", { "id": "group_settings_form", "target": "/groups/update_settings" },
      createDOM( "input",
        { "type": "hidden", "name": "group_id", "class": "group_id", "value": result.group.object_id }
      ),
      createDOM( "p", {},
        createDOM( "b", {}, "group name" ),
        createDOM( "br", {} ),
        createDOM( "input",
          { "type": "text", "name": "group_name", "id": "group_name", "class": "text_field",
            "size": "30", "maxlength": "100", "value": result.group.name }
        )
      ),
      createDOM( "p", {},
        createDOM( "input",
          { "type": "submit", "name": "group_settings_button", "id": "group_settings_button", "class": "button", "value": "save settings" }
        )
      )
    ),
    createDOM( "h3", {}, "create group member" ),
    createDOM( "form", { "id": "create_user_form", "target": "/users/signup_group_member" },
      createDOM( "input",
        { "type": "hidden", "name": "group_id", "class": "group_id", "value": result.group.object_id }
      ),
      createDOM( "p", {},
        createDOM( "b", {}, "new username" ),
        createDOM( "br", {} ),
        createDOM( "input",
          { "type": "text", "name": "username", "id": "username", "class": "text_field",
            "size": "30", "maxlength": "60" }
        )
      ),
      createDOM( "p", {},
        createDOM( "b", {}, "password" ),
        createDOM( "br", {} ),
        createDOM( "input",
          { "type": "password", "name": "password", "id": "password", "class": "text_field",
            "size": "30", "maxlength": "60" }
        )
      ),
      createDOM( "p", {},
        createDOM( "b", {}, "password" ), " (again)",
        createDOM( "br", {} ),
        createDOM( "input",
          { "type": "password", "name": "password_repeat", "id": "password_repeat", "class": "text_field",
            "size": "30", "maxlength": "60" }
        )
      ),
      createDOM( "p", {},
        createDOM( "b", {}, "email address" ),
        createDOM( "br", {} ),
        createDOM( "input",
          { "type": "text", "name": "email_address", "id": "email_address", "class": "text_field",
            "size": "30", "maxlength": "60" }
        )
      ),
      createDOM( "p", {},
        createDOM( "input",
          { "type": "submit", "name": "create_user_button", "id": "create_user_button", "class": "button", "value": "create member" }
        )
      )
    ),
    createDOM( "h3", {}, "group members" ),
    createDOM( "p", {},
      createDOM( "b", {}, "admins" ),
      createDOM( "br", {} ),
      admin_list
    ),
    createDOM( "p", {},
      createDOM( "b", {}, "members" ),
      createDOM( "br", {} ),
      user_list
    )
  );

  for ( var i in result.admin_users ) {
    var user = result.admin_users[ i ];
    appendChildNodes( admin_list, createDOM( "div", { "class": "indented" }, user.username ) );
  }

  if ( result.admin_users.length == 0 )
    appendChildNodes( admin_list, createDOM( "div", { "class": "indented" }, "This group has no admin users." ) );

  for ( var i in result.other_users ) {
    var user = result.other_users[ i ];
    appendChildNodes( user_list, createDOM( "div", { "class": "indented" }, user.username,
      createDOM( "input", {
        "type": "button",
        "id": "remove_user_" + user.object_id + "_" + result.group.object_id,
        "class": "remove_user_button button",
        "value": " x ",
        "title": "remove this user from the group"
      } )
    ) );
  }

  if ( result.other_users.length == 0 )
    appendChildNodes( user_list, createDOM( "div", { "class": "indented" }, "This group has no members." ) );

  this.create_editor( "group_" + result.group.object_id, "<h3>group admin settings</h3>" + div.innerHTML, undefined, undefined, undefined, false, true, false, getElement( "note_settings" ) );
}

Wiki.prototype.display_import_notebook = function ( result ) {
  this.clear_messages();
  this.clear_pulldowns();

  var import_frame = getElement( "note_import" );
  if ( import_frame )
    import_frame.editor.shutdown();

  var form = createDOM( "form", { "id": "import_notebook_form", "target": "/notebooks/import_csv" },
    createDOM( "input",
      { "type": "hidden", "name": "file_id", "value": result.file_id }
    )
  );

  appendChildNodes( form, createDOM( "p", {}, "Here are the first few lines of the file:" ) );

  var tbody = createDOM( "tbody", {} );
  var table = createDOM( "table" , { "id": "import_notebook_table" }, tbody );

  appendChildNodes( form, table );

  for ( var i in result.rows ) {
    var row = result.rows[ i ];
    var row_node = createDOM( "tr", {} );

    for ( var j in row ) {
      var element = row[ j ];
      appendChildNodes( row_node, createDOM( "td", {}, element ) );
    }

    appendChildNodes( tbody, row_node );
  }

  var contents_select = createDOM( "select", { "name": "content_column" } );
  var column_number = 1;

  for ( i in result.rows[ 0 ] ) {
    var element = result.rows[ 0 ][ i ];
    appendChildNodes( contents_select, createDOM( "option", { "value": i }, "column " + column_number + " - " + element ) );
    column_number += 1;
  }

  appendChildNodes( form, createDOM( "p", { "target": "/notebooks/import" },
    createDOM( "b", {}, "Which column contains the note contents text?" ),
    createDOM( "br", {} ),
    contents_select
  ) );

  var titles_select = createDOM( "select", { "name": "title_column" } );
  column_number = 1;

  appendChildNodes( titles_select, createDOM( "option", { "value": "None" }, "There is no title column." ) );
  for ( i in result.rows[ 0 ] ) {
    var element = result.rows[ 0 ][ i ];
    appendChildNodes( titles_select, createDOM( "option", { "value": i }, "column " + column_number + " - " + element ) );
    column_number += 1;
  }

  appendChildNodes( form, createDOM( "p", {},
    createDOM( "b", {}, "Which column contains the note titles (if any)?" ),
    createDOM( "br", {} ),
    titles_select
  ) );

  var plaintext_label = createDOM( "label",
    { "for": "plaintext_radio", "class": "radio_label", "title": "The note contents are just plain text." },
    "plain text"
  );
  var html_label = createDOM( "label",
    { "for": "html_radio", "class": "radio_label", "title": "The note contents are formatted as HTML." },
    "HTML"
  );

  var plaintext_radio = createDOM( "input",
    { "type": "radio", "id": "plaintext_radio", "name": "plaintext", "value": "True", "checked": "true" }
  );
  var html_radio = createDOM( "input",
    { "type": "radio", "id": "html_radio", "name": "plaintext", "value": "False" }
  );

  appendChildNodes( form, createDOM( "p", {},
    createDOM( "b", {}, "Should the note contents be treated as plain text or HTML?" ),
    createDOM( "br", {} ),
    createDOM( "table" , { "id": "plaintext_table", "class": "radio_table" },
      createDOM( "tr", {},
        createDOM( "td", {}, plaintext_radio, plaintext_label ),
        createDOM( "td", {}, html_radio, html_label )
      )
    )
  ) );

  appendChildNodes( form, createDOM( "p", {},
    createDOM( "input",
      { "type": "submit", "name": "import_button", "id": "import_button", "class": "button", "value": "import notebook" }
    )
  ) );

  var div = createDOM( "div", {},
    createDOM( "p", {}, "Almost done. I just need a little information about your file before I can complete the import and create a new notebook." ),
    form,
    createDOM( "p", {}, "Once you begin the import, it may take several seconds to complete." )
  );
  
  this.create_editor( "import", "<h3>import a notebook</h3>" + div.innerHTML, undefined, undefined, undefined, false, true, false, undefined );
}

Wiki.prototype.declutter_clicked = function () {
  var header = getElement( "header" );
  if ( header )
    addElementClass( header, "undisplayed" );

  var link_area_holder = getElement( "link_area_holder" );
  if ( link_area_holder )
    addElementClass( link_area_holder, "undisplayed" );

  var note_tree_area = getElement( "note_tree_area" );
  if ( note_tree_area )
    addElementClass( note_tree_area, "undisplayed" );

  var clutter_link = getElement( "clutter_link" );
  if ( clutter_link ) {
    removeElementClass( clutter_link, "undisplayed" );
  } else {
    clutter_link = createDOM(
      "a",
      { "href": "#", "id": "clutter_link", "title": "Return to the full view of your notebook." },
      "show it all"
    );

    appendChildNodes( "link_area", createDOM( "div", { "class": "link_area_item" }, clutter_link ) );

    var self = this;
    connect( clutter_link, "onclick", function ( event ) {
      self.clutter_clicked();
      event.stop();
    } );
  }
}

Wiki.prototype.clutter_clicked = function () {
  var header = getElement( "header" );
  if ( header )
    removeElementClass( header, "undisplayed" );

  var link_area_holder = getElement( "link_area_holder" );
  if ( link_area_holder )
    removeElementClass( link_area_holder, "undisplayed" );

  var note_tree_area = getElement( "note_tree_area" );
  if ( note_tree_area )
    removeElementClass( note_tree_area, "undisplayed" );

  var clutter_link = getElement( "clutter_link" );
  if ( clutter_link )
    addElementClass( clutter_link, "undisplayed" );
}

Wiki.prototype.move_current_notebook_up = function ( event ) {
  var current_notebook = getElement( "current_notebook_wrapper" );
  var sibling_notebook = current_notebook;

  // find the previous sibling notebook node
  do {
    var sibling_notebook = sibling_notebook.previousSibling;
  } while ( sibling_notebook && sibling_notebook.className != "link_area_item" );

  removeElement( current_notebook );
  if ( sibling_notebook )
    // move the current notebook up before the previous notebook node
    insertSiblingNodesBefore( sibling_notebook, current_notebook );
    // if the current notebook is the first one, wrap it around to the bottom of the list
  else {
    var notebooks_area = getElement( "notebooks_area" );
    appendChildNodes( notebooks_area, current_notebook );
  }

  var self = this;
  this.invoker.invoke( "/notebooks/move_up", "POST", { 
    "notebook_id": this.notebook.object_id
  } );
}

Wiki.prototype.move_current_notebook_down = function ( event ) {
  var current_notebook = getElement( "current_notebook_wrapper" );
  var sibling_notebook = current_notebook;

  // find the next sibling notebook node
  do {
    var sibling_notebook = sibling_notebook.nextSibling;
  } while ( sibling_notebook && sibling_notebook.className != "link_area_item" );

  removeElement( current_notebook );
  if ( sibling_notebook )
    // move the current notebook down after the previous notebook node
    insertSiblingNodesAfter( sibling_notebook, current_notebook );
    // if the current notebook is the last one, wrap it around to the top of the list
  else {
    var notebooks_area_title = getElement( "notebooks_area_title" );
    insertSiblingNodesAfter( notebooks_area_title, current_notebook );
  }

  var self = this;
  this.invoker.invoke( "/notebooks/move_down", "POST", { 
    "notebook_id": this.notebook.object_id
  } );
}

Wiki.prototype.display_message = function ( text, nodes, position_after ) {
  var self = this;
  this.clear_messages();
  this.clear_pulldowns();

  var inner_div = DIV( { "class": "message_inner" }, text + " " );
  for ( var i in nodes )
    appendChildNodes( inner_div, nodes[ i ] );

  var ok_button = createDOM( "input", {
    "type": "button",
    "class": "message_button",
    "value": "ok",
    "title": "dismiss this message"
  } );
  appendChildNodes( inner_div, ok_button );
  connect( ok_button, "onclick", function () { self.clear_messages(); } );

  var div = DIV( { "class": "message" }, inner_div );
  div.nodes = nodes;
  div.init_time = new Date();

  if ( position_after )
    insertSiblingNodesAfter( position_after, div )
  else if ( this.focused_editor )
    insertSiblingNodesAfter( this.focused_editor.holder, div )
  else
    insertSiblingNodesAfter( "notes_top", div );

  this.scroll_to( div );
  this.resize_editor();

  return div;
}

Wiki.prototype.display_error = function ( text, nodes, position_after ) {
  var self = this;
  this.clear_messages();
  this.clear_pulldowns();

  var inner_div = DIV( { "class": "error_inner" }, text + " " );
  for ( var i in nodes )
    appendChildNodes( inner_div, nodes[ i ] );

  ok_button = createDOM( "input", {
    "type": "button",
    "class": "message_button",
    "value": "ok",
    "title": "dismiss this message"
  } );
  appendChildNodes( inner_div, ok_button );
  connect( ok_button, "onclick", function () { self.clear_messages(); } );

  var div = DIV( { "class": "error" }, inner_div );
  div.nodes = nodes;
  div.init_time = new Date();

  if ( position_after )
    insertSiblingNodesAfter( position_after, div )
  else if ( this.focused_editor )
    insertSiblingNodesAfter( this.focused_editor.holder, div )
  else
    insertSiblingNodesAfter( "notes_top", div );

  this.scroll_to( div );
  this.resize_editor();

  return div;
}

Wiki.prototype.scroll_to = function ( node ) {
  // if the message is already completely on-screen, then there's no need to scroll
  var viewport_position = getViewportPosition();
  if ( getElementPosition( node ).y < viewport_position.y ||
       getElementPosition( node ).y + getElementDimensions( node ).h > viewport_position.y + getViewportDimensions().h )
    new ScrollTo( node, { "duration": 0.25 } );
}

Wiki.prototype.clear_messages = function () {
  var message_results = getElementsByTagAndClassName( "div", "message" );
  var error_results = getElementsByTagAndClassName( "div", "error" );

  for ( var i in message_results ) {
    var result = message_results[ i ];

    // only close the message if it's been open at least a quarter second
    if ( new Date() - result.init_time < 250 )
      continue

    blindUp( result, options = { "duration": 0.25, afterFinish: function () {
      try {
        for ( var j in result.nodes )
          disconnectAll( result.nodes[ j ] );
        removeElement( result );
      } catch ( e ) { }
    } } );
  }

  for ( var i in error_results ) {
    var result = error_results[ i ];

    if ( new Date() - result.init_time < 250 )
      continue

    blindUp( result, options = { "duration": 0.25, afterFinish: function () {
      try {
        removeElement( result );
      } catch ( e ) { }
    } } );
  }

  if ( message_results.length || error_results.length )
    this.resize_editor();
}

Wiki.prototype.clear_pulldowns = function ( ephemeral_only ) {
  var results = getElementsByTagAndClassName( "div", "pulldown" );

  for ( var i in results ) {
    var result = results[ i ];

    if ( !result.pulldown )
      continue;

    // only close the pulldown if it's been open at least a quarter second
    if ( new Date() - result.pulldown.init_time < 250 )
      continue
    if ( ephemeral_only && !result.pulldown.ephemeral )
      continue;

    result.pulldown.shutdown();
    result.pulldown = null;
  }
}

Wiki.prototype.delete_all_editors = function ( event ) {
  this.clear_messages();
  this.clear_pulldowns();
  this.editor_focused( null );

  this.startup_notes = new Array();

  if ( this.notebook.read_write == NOTEBOOK_READ_WRITE ) {
    var self = this;
    this.invoker.invoke( "/notebooks/delete_all_notes", "POST", { 
      "notebook_id": this.notebook.object_id
    }, function ( result ) { self.display_storage_usage( result.storage_bytes ); } );
  }

  this.focused_editor = null;

  var divs = getElementsByTagAndClassName( "div", "static_note_div" );
  for ( var i in divs ) {
    var editor = divs[ i ].editor;
    if ( editor )
      editor.shutdown();
  }

  this.zero_total_notes_count();

  var note_tree_root_table = getElement( "note_tree_root_table" );
  if ( note_tree_root_table )
    removeElement( note_tree_root_table );

  this.display_empty_message( true );

  event.stop();
}

Wiki.prototype.display_empty_message = function ( replace_messages ) {
  if ( !replace_messages ) {
    // if there are any messages already open, bail
    var messages = getElementsByTagAndClassName( "div", "message" );
    if ( messages.length > 0 ) return false;

    // if there are any errors open, bail
    var errors = getElementsByTagAndClassName( "div", "error" );
    if ( errors.length > 0 ) return false;
  }

  // if there are any open editors, bail
  if ( Editor.shared_frame && Editor.shared_frame.editor && !Editor.shared_frame.editor.closed )
    return false;
  var divs = getElementsByTagAndClassName( "div", "static_note_div" );
  for ( var i in divs ) {
    var editor = divs[ i ].editor;
    if ( editor && !editor.closed )
      return;
  }

  if ( !this.total_notes_count ) {
    if ( this.parent_id )
      this.display_message( "There are no notes in the trash." )
    else
      this.display_message( "This notebook is empty." );
    return true;
  }

  if ( !replace_messages )
    return true;

  return false;
}

DATE_PATTERN = /(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d).(\d+)[+-](\d\d:?\d\d)/;

Wiki.prototype.brief_revision = function ( revision ) {
  var matches = DATE_PATTERN.exec( revision );

  return new Date( Date.UTC(
    matches[ 1 ],        // year
    matches[ 2 ] - 1,    // month (zero-based)
    matches[ 3 ],        // day
    matches[ 4 ],        // hour
    matches[ 5 ],        // minute
    matches[ 6 ],        // second
    matches[ 7 ] * 0.001 // milliseconds
  ) ).toLocaleString();
}

Wiki.prototype.increment_total_notes_count = function () {
  if ( this.total_notes_count == null ) return;
  this.total_notes_count += 1;
  replaceChildNodes( "total_notes_count", this.total_notes_count );
  signal( this, "total_notes_count_updated", this.total_notes_count );
}

Wiki.prototype.decrement_total_notes_count = function () {
  if ( this.total_notes_count == null ) return;
  this.total_notes_count -= 1;
  replaceChildNodes( "total_notes_count", this.total_notes_count );
  signal( this, "total_notes_count_updated", this.total_notes_count );
}

Wiki.prototype.zero_total_notes_count = function () {
  if ( this.total_notes_count == null ) return;
  this.total_notes_count = 0;
  replaceChildNodes( "total_notes_count", this.total_notes_count );
  signal( this, "total_notes_count_updated", this.total_notes_count );
}

Wiki.prototype.export_clicked = function () {
  var pulldown_id = "export_pulldown";
  var existing_div = getElement( pulldown_id );
  if ( existing_div ) {
    existing_div.pulldown.shutdown();
    existing_div.pulldown = null;
    return;
  }

  new Export_pulldown( this, this.notebook.object_id, this.invoker, getElement( "export_link" ) );
}

Wiki.prototype.import_clicked = function () {
  var pulldown_id = "upload_import";
  var existing_div = getElement( pulldown_id );
  if ( existing_div ) {
    existing_div.pulldown.shutdown();
    existing_div.pulldown = null;
    return;
  }

  new Upload_pulldown( this, this.notebook.object_id, this.invoker, null, null, getElement( "import_link" ) );
}

Wiki.prototype.start_notebook_rename = function () {
  this.clear_pulldowns();

  // if a renaming is already in progress, end the renaming instead of starting one
  var notebook_name_field = getElement( "notebook_name_field" );
  if ( notebook_name_field ) {
    this.end_notebook_rename();
    return; 
  }

  var div = createDOM( "div" );
  div.innerHTML = this.notebook.name;
  var notebook_name = scrapeText( div );

  notebook_name_field = createDOM(
    "input", {
      "type": "text",
      "value": notebook_name,
      "id": "notebook_name_field",
      "name": "notebook_name_field",
      "size": "30",
      "maxlength": "100",
      "class": "text_field"
    }
  );

  var ok_button = createDOM(
    "input", {
      "type": "button",
      "class": "message_button",
      "value": "rename",
      "title": "rename this notebook"
    }
  );

  var rename_form = createDOM(
    "form", { "id": "rename_form" }, notebook_name_field, ok_button
  );

  replaceChildNodes( "notebook_header_name", rename_form );

  var self = this;
  connect( rename_form, "onsubmit", function ( event ) {
    self.end_notebook_rename();
    event.stop();
  } );
  connect( ok_button, "onclick", function ( event ) {
    self.end_notebook_rename();
    event.stop();
  } );
  connect( notebook_name_field, "onclick", function ( event ) {
    event.stop();
  } );

  notebook_name_field.focus();
  notebook_name_field.select();
}

Wiki.prototype.end_notebook_rename = function ( new_notebook_name, prevent_rename_on_click ) {
  if ( !new_notebook_name )
    new_notebook_name = getElement( "notebook_name_field" ).value;

  // if the new name is blank or reserved, don't actually rename the notebook
  if ( /^\s*$/.test( new_notebook_name ) )
    new_notebook_name = this.notebook.name;

  if ( /^\s*Luminotes/.test( new_notebook_name ) || /^\s*trash\s*$/.test( new_notebook_name ) ) {
    new_notebook_name = this.notebook.name;
    this.display_error( "That notebook name is not available. Please try a different one." );
  }

  // rename the notebook in the header
  if ( prevent_rename_on_click ) {
    var notebook_header_name = createDOM(
      "span", {},
      createDOM( "strong", {}, new_notebook_name )
    );
    replaceChildNodes( "notebook_header_area", notebook_header_name );
  } else {
    var notebook_header_name = createDOM(
      "span",
      { "id": "notebook_header_name", "title": "Rename this notebook." },
      createDOM( "strong", {}, new_notebook_name )
    );
    replaceChildNodes( "notebook_header_area", notebook_header_name );

    var self = this;
    connect( notebook_header_name, "onclick", function ( event ) {
      self.start_notebook_rename();
      event.stop();
    } );
  }

  // rename the notebook link on the right side of the page
  var notebook_link = getElement( "notebook_" + this.notebook.object_id );
  if ( notebook_link ) {
    replaceChildNodes( notebook_link, document.createTextNode( new_notebook_name ) );
  }

  // rename the notebook within the rss link (if any)
  var notebook_rss_link = getElement( "notebook_rss_link" );
  if ( notebook_rss_link ) {
    divider = "?rss&notebook_name=";
    pieces = notebook_rss_link.href.split( divider );
    notebook_rss_link.href = pieces[ 0 ] + divider + escape( new_notebook_name );
  }

  // if the name has changed, then send the new name to the server
  if ( new_notebook_name == this.notebook.name )
    return;

  this.notebook.name = new_notebook_name;
  this.invoker.invoke( "/notebooks/rename", "POST", {
    "notebook_id": this.notebook.object_id,
    "name": new_notebook_name
  } );
}

Wiki.prototype.delete_notebook = function () {
  if ( this.focused_editor ) {
    var self = this;
    this.save_editor( this.focused_editor, false, function () {
      self.invoker.invoke( "/notebooks/delete", "POST", {
        "notebook_id": self.notebook.object_id
      } );
    } )
    return;
  }

  this.invoker.invoke( "/notebooks/delete", "POST", {
    "notebook_id": this.notebook.object_id
  } );
}

Wiki.prototype.delete_notebook_forever = function ( event, notebook_id ) {
  var deleted_notebook_node = getElement( "deleted_notebook_" + notebook_id );
  if ( !deleted_notebook_node ) return;

  for ( var i in deleted_notebook_node.childNodes ) {
    var child = deleted_notebook_node.childNodes[ i ];
    disconnectAll( child );
  }

  removeElement( deleted_notebook_node );

  var items = getElementsByTagAndClassName( "div", "deleted_notebook_item" );
  if ( items.length == 0 )
    removeElement( "deleted_notebooks" );

  var self = this;
  this.invoker.invoke( "/notebooks/delete_forever", "POST", {
    "notebook_id": notebook_id
  }, function ( result ) { self.display_storage_usage( result.storage_bytes ); } );

  event.stop();
}

Wiki.prototype.toggle_editor_changes = function ( event, editor ) {
  // if the pulldown is already open, then just close it
  var pulldown_id = "changes_" + editor.id;
  var existing_div = getElement( pulldown_id );
  if ( existing_div ) {
    existing_div.pulldown.shutdown();
    existing_div.pulldown = null;
    return;
  }

  event.stop();

  // if there's already a cached revision list, then display the changes pulldown and bail
  if ( ( editor.user_revisions && editor.user_revisions.length > 0 ) ) {
    new Changes_pulldown( this, this.notebook.object_id, this.invoker, editor );
    return;
  }

  // otherwise, load the revision list for this note from the server
  var self = this;
  this.invoker.invoke(
    "/notebooks/load_note_revisions", "GET", {
      "notebook_id": this.notebook.object_id,
      "note_id": editor.id
    },
    function ( result ) {
      editor.user_revisions = result.revisions;
      new Changes_pulldown( self, self.notebook.object_id, self.invoker, editor );
    }
  );
}

Wiki.prototype.toggle_editor_tools = function ( event, editor ) {
  // if the pulldown is already open, then just close it
  var pulldown_id = "tools_" + editor.id;
  var existing_div = getElement( pulldown_id );
  if ( existing_div ) {
    existing_div.pulldown.shutdown();
    existing_div.pulldown = null;
    return;
  }

  new Tools_pulldown( this, this.notebook.object_id, this.invoker, editor );
  event.stop();
}

connect( window, "onload", function ( event ) { new Wiki( new Invoker() ); } );


function Pulldown( wiki, notebook_id, pulldown_id, anchor, relative_to, ephemeral ) {
  this.wiki = wiki;
  this.notebook_id = notebook_id;
  this.div = createDOM( "div", { "id": pulldown_id, "class": "pulldown" } );
  this.div.pulldown = this;
  this.init_time = new Date();
  this.anchor = anchor;
  this.relative_to = relative_to;
  this.ephemeral = ephemeral;

  addElementClass( this.div, "invisible" );

  appendChildNodes( document.body, this.div );

  if ( this.ephemeral ) {
    // when the mouse cursor is moved into the pulldown, it becomes non-ephemeral (in other words,
    // it will no longer disappear in a few seconds). but as soon as the mouse leaves, it becomes
    // ephemeral again
    var self = this;
    connect( this.div, "onmouseover", function ( event ) {
      self.ephemeral = false;
    } );
    connect( this.div, "onmouseout", function ( event ) {
      self.ephemeral = true;
    } );
  }
}

Pulldown.prototype.finish_init = function () {
  Pulldown.prototype.update_position.call( this );
  removeElementClass( this.div, "invisible" );
}

function calculate_position( node, anchor, relative_to, always_left_align ) {
  var anchor_dimensions = getElementDimensions( anchor );

  // if the anchor's first child is larger (vertically) than its parent, then use it as the anchor
  if ( anchor.firstChild ) {
    try{
      var child_dimensions = getElementDimensions( anchor.firstChild );
      if ( child_dimensions.h > anchor_dimensions.h + 4 ) {
        anchor = anchor.firstChild;
        anchor_dimensions = child_dimensions;
      }
    } catch ( e ) {}
  }

  // position the pulldown under the anchor
  var position = getElementPosition( anchor );

  // in WebKit, work around a bug in which children/grandchildren/etc of relatively positioned
  // elements inside of fixed position elements have an incorrect position
  if ( WEBKIT ) {
    var parent_node = anchor.parentNode;
    var found_fixed_parent = false;

    while ( parent_node ) {
      if ( getStyle( parent_node, "position" ) == "fixed" )
        found_fixed_parent = true;
      else if ( found_fixed_parent && getStyle( parent_node, "position" ) == "relative" ) {
        position.x -= parent_node.offsetLeft;
        position.y -= parent_node.offsetTop;
        break;
      }
      parent_node = parent_node.parentNode;
    }
  }

  if ( relative_to ) {
    var relative_pos = getElementPosition( relative_to );
    if ( relative_pos ) {
      position.x += relative_pos.x;
      position.y += relative_pos.y;

      // adjust the vertical position based on how far the page has scrolled
      position.y -= getElement( "html" ).scrollTop;
    }
  }

  var node_dimensions = getElementDimensions( node );

  // if the position is on the right half of the page, then align the right edge of the node with
  // the right edge of the anchor
  if ( !always_left_align && position.x > getViewportDimensions().w * 0.5 ) {
    if ( node_dimensions )
      position.x = position.x - node_dimensions.w + anchor_dimensions.w;
  }

  // if we still don't have a height, move the position down a bit by an arbitrary amount
  if ( anchor_dimensions.h == 0 )
    position.y += 8;
  else
    position.y += anchor_dimensions.h + 4;

  return position;
}

Pulldown.prototype.update_position = function ( always_left_align ) {
  var position = calculate_position( this.div, this.anchor, this.relative_to, always_left_align );
  setElementPosition( this.div, position );

  var div_height = getElementDimensions( this.div ).h;
  var viewport_bottom = getViewportPosition().y + getViewportDimensions().h;

  // if the pulldown is now partially off the bottom of the window, move it up until it isn't
  if ( position.y + div_height > viewport_bottom )
    new Move( this.div, { "x": position.x, "y": viewport_bottom - div_height, "mode": "absolute", "duration": 0.25 } );
}

Pulldown.prototype.shutdown = function () {
  if ( this.div && this.div.parentNode )
    removeElement( this.div );
}


function Tools_pulldown( wiki, notebook_id, invoker, editor ) {
  Pulldown.call( this, wiki, notebook_id, "tools_" + editor.id, editor.tools_button );

  this.invoker = invoker;
  this.editor = editor;
  this.startup_checkbox = createDOM( "input", { "type": "checkbox", "class": "pulldown_checkbox", "id": "startup_checkbox" } );
  this.startup_label = createDOM( "label", { "for": "startup_checkbox", "class": "pulldown_label", "title": "Display this note whenever the notebook is loaded." },
    "show on startup"
  );
  appendChildNodes( this.div, createDOM( "div", {}, this.startup_checkbox, this.startup_label ) );

  this.unformat_checkbox = createDOM( "input", { "type": "checkbox", "class": "pulldown_checkbox invisible" } );
  this.unformat_link = createDOM( "a",
    {
      "href": "#",
      "class": "pulldown_link",
      "title": "Remove formatting from the currently selected text."
    },
    "remove formatting"
  );
  appendChildNodes( this.div, createDOM( "div", {}, this.unformat_checkbox, this.unformat_link ) );

  if ( !editor.empty() ) {
    this.print_checkbox = createDOM( "input", { "type": "checkbox", "class": "pulldown_checkbox invisible" } );
    this.print_link = createDOM( "a",
      {
        "href": "/notebooks/export?notebook_id=" + notebook_id + "&note_id=" + editor.id + "&format=print",
        "target": "_new",
        "class": "pulldown_link",
        "title": "Print this note by itself."
      },
      "print this note"
    );
    appendChildNodes( this.div, createDOM( "div", {}, this.print_checkbox, this.print_link ) );
  }

  this.startup_checkbox.checked = editor.startup;

  var self = this;
  connect( this.startup_checkbox, "onclick", function ( event ) { self.startup_clicked( event ); } );
  connect( this.unformat_link, "onclick", function ( event ) { self.unformat_clicked( event ); } );
  if ( this.print_link )
    connect( this.print_link, "onclick", function ( event ) { self.print_clicked( event ); } );

  Pulldown.prototype.finish_init.call( this );
}

Tools_pulldown.prototype = new function () { this.prototype = Pulldown.prototype; };
Tools_pulldown.prototype.constructor = Tools_pulldown;

Tools_pulldown.prototype.startup_clicked = function ( event ) {
  this.editor.startup = this.startup_checkbox.checked;
  this.editor.mark_dirty();

  // save this note along with its toggled startup state
  this.wiki.save_editor( this.editor );
}

Tools_pulldown.prototype.unformat_clicked = function ( event ) {
  event.stop();

  if ( !this.editor.unformat_selection() )
    this.wiki.display_message( "To remove the formatting from some text in this note, first highlight the text that you'd like to be unformatted." );

  this.shutdown();
}

Tools_pulldown.prototype.print_clicked = function ( event ) {
  this.wiki.editor_focused( null, true );
}

Tools_pulldown.prototype.shutdown = function () {
  Pulldown.prototype.shutdown.call( this );

  disconnectAll( this.startup_checkbox );
  if ( this.print_link )
    disconnectAll( this.print_link );
}


function Changes_pulldown( wiki, notebook_id, invoker, editor ) {
  Pulldown.call( this, wiki, notebook_id, "changes_" + editor.id, editor.changes_button );

  this.invoker = invoker;
  this.editor = editor;
  this.links = new Array();
  
  if ( !editor.user_revisions || editor.user_revisions.length == 0 ) {
    appendChildNodes( this.div, createDOM( "span", "This note has no previous changes." ) );
    Pulldown.prototype.finish_init.call( this );
    return;
  }

  // display list of revision timestamps in reverse chronological order
  var user_revisions = clone( editor.user_revisions );
  user_revisions.reverse();

  var self = this;
  for ( var i = 0; i < user_revisions.length - 1; ++i ) { // -1 to skip the oldest revision
    var user_revision = user_revisions[ i ];
    var previous_revision = user_revisions[ i + 1 ];

    var short_revision = this.wiki.brief_revision( user_revision.revision );
    var href = "/notebooks/" + this.notebook_id + "?" + queryString(
      [ "note_id", "revision", "previous_revision" ],
      [ this.editor.id, user_revision.revision, previous_revision.revision ]
    );

    var link = createDOM(
      "a",
      { "href": href, "class": "pulldown_link" },
      short_revision + ( ( user_revision.username && user_revision.username != "desktopuser" )
                         ? " by " + user_revision.username : "" )
    );

    this.links.push( link );
    link.revision = user_revision.revision;
    link.previous_revision = previous_revision.revision;
    connect( link, "onclick", function ( event ) { self.link_clicked( event, self.editor.id ); } );
    appendChildNodes( this.div, link );
    appendChildNodes( this.div, createDOM( "br" ) );
  }

  Pulldown.prototype.finish_init.call( this );
}

Changes_pulldown.prototype = new function () { this.prototype = Pulldown.prototype; };
Changes_pulldown.prototype.constructor = Changes_pulldown;

Changes_pulldown.prototype.link_clicked = function( event, note_id ) {
  var revision = event.target().revision;
  var previous_revision = event.target().previous_revision;
  this.wiki.load_editor( "Revision not found.", note_id, revision, previous_revision, null, this.editor.holder );
  event.stop();
}

Changes_pulldown.prototype.shutdown = function () {
  Pulldown.prototype.shutdown.call( this );

  for ( var i in this.links )
    disconnectAll( this.links[ i ] );
}


function Link_pulldown( wiki, notebook_id, invoker, editor, link, ephemeral ) {
  link.pulldown = this;
  this.link = link;

  Pulldown.call( this, wiki, notebook_id, "link_" + editor.id, link, editor.iframe, ephemeral );

  this.invoker = invoker;
  this.editor = editor;
  this.title_field = createDOM( "input", { "class": "text_field", "size": "30", "maxlength": "256" } );
  this.note_summary = createDOM( "span", {} );
  this.previous_title = "";
  this.suggest_pulldown = null;

  var self = this;
  connect( this.title_field, "onclick", function ( event ) { self.title_field_clicked( event ); } );
  connect( this.title_field, "onfocus", function ( event ) { self.title_field_focused( event ); } );
  connect( this.title_field, "onkeydown", function ( event ) { self.title_field_key_pressed( event ); } );
  connect( this.title_field, "onkeyup", function ( event ) { self.title_field_key_released( event ); } );

  // the timeout prevents a race condition between these handlers and a suggesting being clicked
  connect( this.title_field, "onchange", function ( event ) {
    setTimeout( function () { self.title_field_changed( event ); }, 250 );
  } );
  connect( this.title_field, "onblur", function ( event ) {
    setTimeout( function () { self.title_field_changed( event ); }, 250 );
  } );

  appendChildNodes( this.div, createDOM( "span", { "class": "field_label" }, "links to: " ) );
  appendChildNodes( this.div, this.title_field );
  appendChildNodes( this.div, this.note_summary );

  // links with targets are considered links to external sites
  if ( link.target ) {
    this.title_field.value = link.href;
    replaceChildNodes( this.note_summary, "web link" );
    Pulldown.prototype.finish_init.call( this );
    return;
  }

  var query = parse_query( link );
  var title = link_title( link, query );
  var id = query.note_id;

  // if the note has no destination note id set, try loading the note from the server by title
  if ( ( id == undefined || id == "new" || id == "null" ) && title.length > 0 ) {
    if ( title == "search results" ) {
      this.title_field.value = title;
      this.display_summary( title, "current search results" );
      Pulldown.prototype.finish_init.call( this );
      return;
    }

    if ( title == "share this notebook" ) {
      this.title_field.value = title;
      this.display_summary( title, "share this notebook with others" );
      Pulldown.prototype.finish_init.call( this );
      return;
    }

    if ( title == "account settings" ) {
      this.title_field.value = title;
      this.display_summary( title, "account settings" );
      Pulldown.prototype.finish_init.call( this );
      return;
    }

    this.invoker.invoke(
      "/notebooks/load_note_by_title", "GET", {
        "notebook_id": this.notebook_id,
        "note_title": title,
        "summarize": true
      },
      function ( result ) {
        // if the user has already started typing something, don't overwrite it
        if ( self.title_field.value.length != 0 ) {
          Pulldown.prototype.finish_init.call( self );
          return;
        }
        if ( result.note ) {
          self.title_field.value = result.note.title;
          self.display_summary( result.note.title, result.note.summary );
        } else {
          self.title_field.value = title;
          replaceChildNodes( self.note_summary, "empty note" );
        }
      }
    );
    Pulldown.prototype.finish_init.call( this );
    return;
  }

  // if this link has an actual destination note id set, then see if that note is already open. if
  // so, display its title and a summary of its contents
  var destination_editor = editor_by_id( id );
  if ( destination_editor ) {
    this.title_field.value = destination_editor.title;
    this.display_summary( destination_editor.title, destination_editor.summarize() );
    Pulldown.prototype.finish_init.call( this );
    return;
  }

  // otherwise, load the destination note from the server, displaying its title and a summary of
  // its contents
  this.invoker.invoke(
    "/notebooks/load_note", "GET", {
      "notebook_id": this.notebook_id,
      "note_id": id,
      "summarize": true
    },
    function ( result ) {
      // if the user has already started typing something, don't overwrite it
      if ( self.title_field.value.length != 0 ) {
        Pulldown.prototype.finish_init.call( self );
        return;
      }
      if ( result.note ) {
        self.title_field.value = result.note.title;
        self.display_summary( result.note.title, result.note.summary );
      } else {
        self.title_field.value = title;
        replaceChildNodes( self.note_summary, "empty note" );
      }
    }
  );

  Pulldown.prototype.finish_init.call( this );
}

Link_pulldown.prototype = new function () { this.prototype = Pulldown.prototype; };
Link_pulldown.prototype.constructor = Link_pulldown;

Link_pulldown.prototype.display_summary = function ( title, summary ) {
  if ( !summary )
    replaceChildNodes( this.note_summary, "empty note" );
  else if ( summary.length == 0 )
    replaceChildNodes( this.note_summary, "empty note" );
  else
    replaceChildNodes( this.note_summary, summary );
}

Link_pulldown.prototype.title_field_clicked = function ( event ) {
  disconnectAll( this.div );
  this.ephemeral = false;

  event.stop();
}

Link_pulldown.prototype.title_field_focused = function ( event ) {
  disconnectAll( this.div );
  this.ephemeral = false;

  this.title_field.select();
}

Link_pulldown.prototype.update_title_field_with_suggestion = function ( note ) {
  this.title_field.value = note.title;
  this.title_field_changed( null, note );

  if ( this.suggest_pulldown ) {
    this.suggest_pulldown.shutdown();
    this.suggest_pulldown = null;
  }
}

Link_pulldown.prototype.title_field_changed = function ( event, note ) {
  // if the title is actually unchanged, then bail
  var title = strip( this.title_field.value );
  if ( title == this.previous_title )
    return;

  replaceChildNodes( this.note_summary, "" );
  this.previous_title = title;
  var self = this;

  // if a destination note is given, then update the link to point to it
  if ( note ) {
    this.link.href = "/notebooks/" + this.notebook_id + "?note_id=" + note.object_id;
    this.suggest_pulldown.shutdown();
    this.suggest_pulldown = null;

    this.display_summary( note.title, summarize_html( note.contents, note.title ) );
  // otherwise, try to resolve the link title
  } else {
    this.wiki.resolve_link( title, this.link, true, function ( summary ) {
      self.display_summary( title, summary );
    } );
  }
}

Link_pulldown.prototype.title_field_key_pressed = function ( event ) {
  // if enter is pressed, consider the title field altered. this is necessary because IE neglects
  // to issue an onchange event when enter is pressed in an input field
  if ( event.key().code == 13 &&
       ( this.suggest_pulldown == null || this.suggest_pulldown.something_selected() == false ) ) {
    this.title_field_changed();
    event.stop();
  }
}

Link_pulldown.prototype.title_field_key_released = function ( event ) {
  var self = this;

  if ( this.suggest_pulldown ) {
    this.suggest_pulldown.update_suggestions( this.title_field.value );
  } else if ( event.key().code != 13 ) {
    this.suggest_pulldown = new Suggest_pulldown( this.wiki, this.notebook_id, this.invoker, this.title_field, null, this.title_field.value, this.title_field );
    connect( this.suggest_pulldown, "suggestion_selected", function ( note ) {
      self.update_title_field_with_suggestion( note )
    } );
  }
}

Link_pulldown.prototype.update_position = function ( always_left_align ) {
  Pulldown.prototype.update_position.call( this, always_left_align );

  if ( this.suggest_pulldown )
    this.suggest_pulldown.update_position( always_left_align );
}

Link_pulldown.prototype.shutdown = function () {
  if ( this.suggest_pulldown )
    this.suggest_pulldown.shutdown();

  Pulldown.prototype.shutdown.call( this );

  disconnectAll( this.title_field );
  if ( this.link )
    this.link.pulldown = null;
}


function base_upload_filename() {
  // get the basename of the file
  var filename = getElement( "upload" ).value;
  var pieces = filename.split( "/" );
  filename = pieces[ pieces.length - 1 ];
  pieces = filename.split( "\\" );
  filename = pieces[ pieces.length - 1 ];

  return filename;
}


function Upload_pulldown( wiki, notebook_id, invoker, editor, link, anchor, ephemeral ) {
  this.link = link || ( editor ? editor.find_link_at_cursor() : null );
  if ( this.link )
    this.link.pulldown = this;

  Pulldown.call(
    this, wiki, notebook_id,
    "upload_" + ( editor ? editor.id : "import" ),
    this.link || anchor,
    editor ? editor.iframe : null,
    ephemeral
  );

  wiki.down_image_button( "attachFile" );

  this.invoker = invoker;
  this.editor = editor;
  this.iframe = createDOM( "iframe", {
    "src": "about:blank",
    "id": "upload_frame",
    "name": "upload_frame",
    "class": "upload_frame undisplayed"
  } );
  this.iframe.pulldown = this;

  this.file_id = null;
  this.uploading = false;
  this.poller = null;
  this.poll_interval = 250; // in milliseconds, expontentially backing off. see update_progress()
  this.starting_count = 0;

  var self = this;

  appendChildNodes( this.div, this.iframe );

  this.upload_area = createDOM( "span" );
  this.upload_button = createDOM( "input", { "id": "upload_button", "type": "submit", "class": "button", "value": "upload" } );
  appendChildNodes( this.upload_area, createDOM( "form",
    {
      "target": "upload_frame",
      "action": "/files/upload?X-Progress-ID=new&file_id=new",
      "method": "post",
      "enctype": "multipart/form-data",
      "id": "upload_form"
    },
    createDOM( "span", { "class": "field_label" }, this.link ? "attach file: " : "import file: " ),
    createDOM( "input", { "name": "notebook_id", "id": "notebook_id", "type": "hidden", "value": notebook_id } ),
    createDOM( "input", { "name": "note_id", "id": "note_id", "type": "hidden", "value": editor ? editor.id : "" } ),
    createDOM( "input", { "name": "upload", "id": "upload", "type": "file", "class": "text_field", "size": "30" } ),
    this.upload_button
  ) );
  this.upload_button.disabled = true;

  appendChildNodes( this.upload_area, createDOM( "p", {},
                    this.link ? "Please select a file to upload." : "Please select a CSV file of notes to import into a new notebook." ) );
  appendChildNodes( this.upload_area, createDOM( "span", { "id": "tick_preload" } ) );
  appendChildNodes( this.upload_area, createDOM( "input", { "name": "file_id", "id": "file_id", "type": "hidden", "value": "new" } ) );
  appendChildNodes( this.div, this.upload_area );

  connect( this.upload_button, "onclick", function ( event ) {
    self.upload_started();
  } );

  // grab the next available file id
  this.invoker.invoke( "/files/upload_id", "POST",
    { "notebook_id": notebook_id, "note_id": editor ? editor.id : "" },
    function( result ) { self.update_file_id( result ); }
  );

  Pulldown.prototype.finish_init.call( this );
}

Upload_pulldown.prototype = new function () { this.prototype = Pulldown.prototype; };
Upload_pulldown.prototype.constructor = Upload_pulldown;

Upload_pulldown.prototype.update_file_id = function ( result ) {
  this.file_id = result.file_id;

  var upload_form = getElement( "upload_form" )
  if ( upload_form )
    upload_form.action = "/files/upload?X-Progress-ID=" + this.file_id;

  var file_id_node = getElement( "file_id" );
  if ( file_id_node )
    file_id_node.value = this.file_id;

  this.upload_button.disabled = false;
}

Upload_pulldown.prototype.upload_started = function ( file_id ) {
  this.uploading = true;
  var filename = base_upload_filename();

  // if the current title is blank, replace the title with the upload's filename
  if ( this.link ) {
    var title = link_title( this.link );
    if ( title == "" )
      this.link.innerHTML = filename;
  }
  
  this.cancel_button = createDOM( "input", { "type": "submit", "id": "cancel_button", "class": "button", "value": "cancel" } );

  var progress_area = createDOM( "table", {},
    createDOM( "tr", {},
      createDOM( "td", { "class": "field_label", "colspan": "2" }, "uploading " + filename + ": " )
    ),
    createDOM( "tr", { "id": "progress_row" },
      createDOM( "td", {},
        createDOM( "div", { "id": "progress_border" },
          createDOM( "img", { "src": "/static/images/tick.png", "id": "progress_bar" } )
        )
      ),
      createDOM( "td", { "class": "progress_right" },
        createDOM( "span", { "id": "progress_percent" }, "0%" ),
        this.cancel_button
      )
    )
  );

  disconnectAll( this.upload_button );
  addElementClass( this.upload_area, "undisplayed" );
  appendChildNodes( this.div, progress_area );
  this.upload_button = null;

  var self = this;
  connect( this.cancel_button, "onclick", function ( event ) {
    self.cancel_due_to_click();
  } );

  // start polling for the upload progress
  this.poller = setTimeout( function () { self.update_progress(); }, this.poll_interval );
}

Upload_pulldown.prototype.update_progress = function () {
  var self = this;
  var BAR_WIDTH_EM = 20.0;

  this.invoker.invoke( "/files/progress", "GET",
    { "X-Progress-ID": this.file_id },
    function( result ) {
      var fraction_done = 0.0;
      if ( !self.uploading )
        return;

      if ( result.state == "starting" )
        self.starting_count += 1;
      else
        self.starting_count = 0;

      // if ten consecutive "starting" states in a row, bail
      if ( self.starting_count >= 10 ) {
        self.cancel_due_to_error( "A timeout error occurred when uploading the file." );
        return
      }

      if ( result.state == "error" ) {
        if ( result.status == 413 )
          self.cancel_due_to_quota();
        else
          self.cancel_due_to_error( "An error occurred when uploading the file." );
        return;
      }

      if ( result.state == "uploading" && result.size > 0 ) {
        fraction_done = Math.min( result.received / result.size, 1.0 );
        if ( fraction_done > 0.99 )
          fraction_done = 0.99;
      } else if ( result.state == "done" ) {
        fraction_done = 1.0;
      }

      if ( fraction_done > 0.0 ) {
        var percent = fraction_done * 100.0;
        setElementDimensions( "progress_bar", { "w": fraction_done * BAR_WIDTH_EM }, "em" );
        replaceChildNodes( "progress_percent", parseInt( percent ) + "%" );
      }

      // the brief delay gives a brief moment for the progress bar to appear at 100%
      if ( result.state == "done" )
        setTimeout( function () { self.upload_complete(); }, 1 );
      else {
        // capped exponential back-off
        var CAP = 2000;
        if ( self.poll_interval < CAP ) {
          self.poll_interval *= 1.1;
          if ( self.poll_interval > CAP )
            self.poll_interval = CAP;
        }
          
        this.poller = setTimeout( function () { self.update_progress(); }, self.poll_interval );
      }
    }
  );
};

Upload_pulldown.prototype.upload_complete = function () {
  if ( /MSIE/.test( navigator.userAgent ) )
    var quote_filename = true;
  else
    var quote_filename = false;

  // now that the upload is done, the file link should point to the uploaded file
  this.uploading = false;
  if ( this.link ) {
    this.link.href = "/files/download?file_id=" + this.file_id + "&quote_filename=" + quote_filename;
    new File_link_pulldown( this.wiki, this.notebook_id, this.invoker, this.editor, this.link );
  // if there's no link, then assume a CSV file was imported, so display it
  } else {
    var wiki = this.wiki;
    this.invoker.invoke(
      "/files/csv_head", "GET", {
        "file_id": this.file_id
      },
      function ( result ) { wiki.display_import_notebook( result ); }
    );
  }

  this.shutdown();
}

Upload_pulldown.prototype.update_position = function ( always_left_align ) {
  Pulldown.prototype.update_position.call( this, always_left_align );
}

Upload_pulldown.prototype.cancel_due_to_click = function () {
  // when the uploading iframe closes, that should effectively cancel the upload
  this.uploading = false;
  this.wiki.display_message( "The file upload has been cancelled." )
  this.shutdown();
}

Upload_pulldown.prototype.cancel_due_to_quota = function () {
  this.uploading = false;
  this.shutdown();

  this.wiki.display_error(
    "That file is too large for your available storage space. Before uploading, please delete some notes or files, empty the trash, or",
    [ createDOM( "a", { "href": "/pricing" }, "upgrade" ), " your account." ]
  );
}

Upload_pulldown.prototype.cancel_due_to_error = function ( message ) {
  this.uploading = false;
  this.wiki.display_error( message )
  this.shutdown();
}

Upload_pulldown.prototype.shutdown = function () {
  if ( this.uploading )
    return;

  if ( this.poller )
    clearTimeout( this.poller );

  if ( this.upload_button )
    disconnectAll( this.upload_button );

  if ( this.cancel_button )
    disconnectAll( this.cancel_button );

  // in Internet Explorer, the upload won't actually cancel without an explicit Stop command
  if ( !this.iframe.contentDocument && this.iframe.contentWindow )
    this.iframe.contentWindow.document.execCommand( 'Stop' );

  Pulldown.prototype.shutdown.call( this );
  if ( this.link )
    this.link.pulldown = null;
}


function Export_pulldown( wiki, notebook_id, invoker, anchor ) {
  Pulldown.call( this, wiki, notebook_id, "export_pulldown", anchor, null, false );

  this.invoker = invoker;
  this.html_link = createDOM( "a", {
      "href": "/notebooks/export?notebook_id=" + notebook_id + "&format=html",
      "class": "pulldown_label",
      "title": "Download this notebook as a stand-alone HTML web page."
    },
    "HTML web page"
  );
  this.csv_link = createDOM( "a", {
      "href": "/notebooks/export?notebook_id=" + notebook_id + "&format=csv",
      "class": "pulldown_label",
      "title": "Download this notebook as a CSV spreadsheet file."
    },
    "CSV spreadsheet"
  );

  appendChildNodes( this.div, createDOM( "div", {}, this.html_link ) );
  appendChildNodes( this.div, createDOM( "div", {}, this.csv_link ) );

  Pulldown.prototype.finish_init.call( this );
}

Export_pulldown.prototype = new function () { this.prototype = Pulldown.prototype; };
Export_pulldown.prototype.constructor = Export_pulldown;

Export_pulldown.prototype.shutdown = function () {
  Pulldown.prototype.shutdown.call( this );
}


SMALL_MAX_IMAGE_SIZE = 125;
MEDIUM_MAX_IMAGE_SIZE = 300;
LARGE_MAX_IMAGE_SIZE = 500;


function File_link_pulldown( wiki, notebook_id, invoker, editor, link, ephemeral ) {
  link.pulldown = this;
  this.link = link;

  Pulldown.call( this, wiki, notebook_id, "file_link_" + editor.id, link, editor.iframe, ephemeral );

  this.invoker = invoker;
  this.editor = editor;
  this.filename_field = createDOM( "input", { "class": "text_field", "size": "30", "maxlength": "256" } );
  this.file_size = createDOM( "span", {} );
  this.previous_filename = "";
  this.link_title = null;

  var self = this;
  connect( this.filename_field, "onclick", function ( event ) { self.filename_field_clicked( event ); } );
  connect( this.filename_field, "onfocus", function ( event ) { self.filename_field_focused( event ); } );
  connect( this.filename_field, "onchange", function ( event ) { self.filename_field_changed( event ); } );
  connect( this.filename_field, "onblur", function ( event ) { self.filename_field_changed( event ); } );
  connect( this.filename_field, "onkeydown", function ( event ) { self.filename_field_key_pressed( event ); } );

  this.delete_button = createDOM( "input", {
    "type": "button",
    "class": "button",
    "value": "delete",
    "title": "delete file"
  } );

  var query = parse_query( link );
  this.file_id = query.file_id;

  if ( /MSIE/.test( navigator.userAgent ) )
    var quote_filename = true;
  else
    var quote_filename = false;

  this.thumbnail_span = createDOM( "span", {},
    createDOM( "a", { href: "/files/download?file_id=" + this.file_id + "&quote_filename=" + quote_filename, target: "_new" },
      createDOM( "img", { "src": "/files/thumbnail?file_id=" + this.file_id, "class": "file_thumbnail" } )
    )
  );
  appendChildNodes( this.div, this.thumbnail_span );

  // if the link is an image thumbnail link, update the contents of the file link pulldown accordingly
  var image = getFirstElementByTagAndClassName( "img", null, this.link );
  var embed_attributes = { "type": "checkbox", "class": "pulldown_checkbox", "id": "embed_checkbox" };
  var small_size_attributes = { "type": "radio", "id": "small_size_radio", "name": "size", "value": "small" };
  var medium_size_attributes = { "type": "radio", "id": "medium_size_radio", "name": "size", "value": "medium" };
  var large_size_attributes = { "type": "radio", "id": "large_size_radio", "name": "size", "value": "large" };
  var left_justify_attributes = { "type": "radio", "id": "left_justify_radio", "name": "justify", "value": "left" };
  var center_justify_attributes = { "type": "radio", "id": "center_justify_radio", "name": "justify", "value": "center" };
  var right_justify_attributes = { "type": "radio", "id": "right_justify_radio", "name": "justify", "value": "right" };

  if ( image ) {
    addElementClass( this.thumbnail_span, "undisplayed" );
    embed_attributes[ "checked" ] = "true";

    var src = parseQueryString( image.src.split( "?" ).pop() );
    var max_size = src[ "max_size" ];
    if ( max_size == LARGE_MAX_IMAGE_SIZE )
      large_size_attributes[ "checked" ] = "true";
    else if ( max_size == MEDIUM_MAX_IMAGE_SIZE )
      medium_size_attributes[ "checked" ] = "true";
    else
      small_size_attributes[ "checked" ] = "true";

    if ( hasElementClass( image, "center_justified" ) )
      center_justify_attributes[ "checked" ] = "true";
    else if ( hasElementClass( image, "right_justified" ) )
      right_justify_attributes[ "checked" ] = "true";
    else
      left_justify_attributes[ "checked" ] = "true";
  } else {
    small_size_attributes[ "checked" ] = "true";
    left_justify_attributes[ "checked" ] = "true";
  }

  this.embed_checkbox = createDOM( "input", embed_attributes );
  this.small_size_radio = createDOM( "input", small_size_attributes );
  this.medium_size_radio = createDOM( "input", medium_size_attributes );
  this.large_size_radio = createDOM( "input", large_size_attributes );
  this.left_justify_radio = createDOM( "input", left_justify_attributes );
  this.center_justify_radio = createDOM( "input", center_justify_attributes );
  this.right_justify_radio = createDOM( "input", right_justify_attributes );

  var embed_label = createDOM( "label", { "for": "embed_checkbox", "class": "pulldown_label", "title": "Embed this image within the note itself." },
    "show image within note"
  );

  var small_size_label = createDOM( "label",
    { "for": "small_size_radio", "class": "radio_label", "title": "Display a small thumbnail of this image." },
    "small"
  );
  var medium_size_label = createDOM( "label",
    { "for": "medium_size_radio", "class": "radio_label", "title": "Display a medium thumbnail of this image." },
    "medium"
  );
  var large_size_label = createDOM( "label",
    { "for": "large_size_radio", "class": "radio_label", "title": "Display a large thumbnail of this image." },
    "large"
  );

  var left_justify_label = createDOM( "label",
    { "for": "left_justify_radio", "class": "radio_label", "title": "Left justify this image within the note." },
    "left"
  );
  var center_justify_label = createDOM( "label",
    { "for": "center_justify_radio", "class": "radio_label", "title": "Center this image horizontally within the note." },
    "center"
  );
  var right_justify_label = createDOM( "label",
    { "for": "right_justify_radio", "class": "radio_label", "title": "Right justify this image within the note." },
    "right"
  );

  this.image_settings_area = createDOM( "div", { "class": "undisplayed" },
    createDOM( "table" , { "id": "image_settings_table" },
      createDOM( "tbody", {},
        createDOM( "tr", {},
          createDOM( "td", { "class": "field_label" }, "size: " ),
          createDOM( "td", {}, this.small_size_radio, small_size_label ),
          createDOM( "td", {}, this.medium_size_radio, medium_size_label ),
          createDOM( "td", {}, this.large_size_radio, large_size_label )
        ),
        createDOM( "tr", {},
          createDOM( "td", { "class": "field_label" }, "position: " ),
          createDOM( "td", {}, this.left_justify_radio, left_justify_label ),
          createDOM( "td", {}, this.center_justify_radio, center_justify_label ),
          createDOM( "td", {}, this.right_justify_radio, right_justify_label )
        )
      )
    )
  );

  if ( image )
    removeElementClass( this.image_settings_area, "undisplayed" );

  appendChildNodes( this.div, createDOM( "span", { "class": "field_label" }, "filename: " ) );
  appendChildNodes( this.div, this.filename_field );
  appendChildNodes( this.div, this.file_size );
  appendChildNodes( this.div, " " );
  appendChildNodes( this.div, this.delete_button );
  appendChildNodes( this.div, createDOM( "div", {}, this.embed_checkbox, embed_label ) );
  appendChildNodes( this.div, this.image_settings_area );

  // get the file's name and size from the server
  this.invoker.invoke(
    "/files/stats", "GET", {
      "file_id": this.file_id
    },
    function ( result ) {
      // if the user has already started typing something, don't overwrite it
      if ( self.filename_field.value.length == 0 ) {
        self.filename_field.value = result.filename;
        self.previous_filename = result.filename;
      }
      replaceChildNodes( self.file_size, bytes_to_megabytes( result.size_bytes, true ) );
      self.wiki.display_storage_usage( result.storage_bytes );
    }
  );

  connect( this.delete_button, "onclick", function ( event ) { self.delete_button_clicked( event ); } );
  connect( this.embed_checkbox, "onclick", function ( event ) { self.embed_clicked( event ); } );
  connect( this.small_size_radio, "onclick", function ( event ) { self.resize_image( event, "small" ); } );
  connect( this.medium_size_radio, "onclick", function ( event ) { self.resize_image( event, "medium" ); } );
  connect( this.large_size_radio, "onclick", function ( event ) { self.resize_image( event, "large" ); } );
  connect( this.left_justify_radio, "onclick", function ( event ) { self.justify_image( event, "left" ); } );
  connect( this.center_justify_radio, "onclick", function ( event ) { self.justify_image( event, "center" ); } );
  connect( this.right_justify_radio, "onclick", function ( event ) { self.justify_image( event, "right" ); } );

  editor.focus();
  Pulldown.prototype.finish_init.call( this );
}

File_link_pulldown.prototype = new function () { this.prototype = Pulldown.prototype; };
File_link_pulldown.prototype.constructor = File_link_pulldown;

File_link_pulldown.prototype.filename_field_clicked = function ( event ) {
  event.stop();
}

File_link_pulldown.prototype.filename_field_focused = function ( event ) {
  this.filename_field.select();
}

File_link_pulldown.prototype.filename_field_changed = function ( event ) {
  // if the filename is actually unchanged, then bail
  var filename = strip( this.filename_field.value );
  if ( filename == "" || filename == this.previous_filename )
    return;

  var title = link_title( this.link );
  if ( title == this.previous_filename )
    replaceChildNodes( this.link, this.editor.document.createTextNode( filename ) );

  this.previous_filename = filename;

  this.invoker.invoke(
    "/files/rename", "POST", {
      "file_id": this.file_id,
      "filename": filename
    }
  );
}

File_link_pulldown.prototype.filename_field_key_pressed = function ( event ) {
  // if enter is pressed, consider the title field altered. this is necessary because IE neglects
  // to issue an onchange event when enter is pressed in an input field
  if ( event.key().code == 13 ) {
    this.filename_field_changed();
    event.stop();
  }
}

File_link_pulldown.prototype.delete_button_clicked = function ( event ) {
  var self = this;

  // change the embedded image (if any) back into a plain file link before deletion
  if ( getFirstElementByTagAndClassName( "img", null, this.link ) )
    this.link.innerHTML = this.link_title || this.filename_field.value || this.previous_filename;

  this.invoker.invoke(
    "/files/delete", "POST", {
      "file_id": this.file_id
    },
    function ( result ) { self.wiki.display_storage_usage( result.storage_bytes ); }
  );

  this.link.href = "/files/new";
  this.editor.focus();

  this.wiki.display_message( 'The file "' + strip( this.filename_field.value ) + '" has been deleted.' );
}

File_link_pulldown.prototype.embed_clicked = function ( event ) {
  if ( this.embed_checkbox.checked ) {
    var image = createDOM( "img", { "src": "/files/thumbnail?file_id=" + this.file_id + "&max_size=" + SMALL_MAX_IMAGE_SIZE, "class": "left_justified" } );
    var image_span = createDOM( "span", {}, image );
    this.link_title = link_title( this.link );
    this.link.innerHTML = image_span.innerHTML;
    addElementClass( this.thumbnail_span, "undisplayed" );
    removeElementClass( this.image_settings_area, "undisplayed" );
  } else {
    this.justify_image( "left" );
    this.left_justify_radio.checked = true;
    this.small_size_radio.checked = true;
    removeElementClass( this.thumbnail_span, "undisplayed" );
    addElementClass( this.image_settings_area, "undisplayed" );
    this.link.innerHTML = this.link_title || this.filename_field.value || this.previous_filename;
  }

  this.update_position();
  this.editor.resize();
}

File_link_pulldown.prototype.resize_image = function ( event, position ) {
  var image = getFirstElementByTagAndClassName( "img", null, this.link );
  if ( !image )
    return;

  if ( position == "large" ) {
    var max_size = LARGE_MAX_IMAGE_SIZE;
  } else if ( position == "medium" ) {
    var max_size = MEDIUM_MAX_IMAGE_SIZE;
  } else {
    var max_size = SMALL_MAX_IMAGE_SIZE;
  }

  // when the newly resized image finishes loading, update the pulldown position and resize the
  // editor
  var self = this;
  connect( image, "onload", function () {
    self.update_position();
    self.editor.resize();
  } );

  image.setAttribute( "src", "/files/thumbnail?file_id=" + this.file_id + "&max_size=" + max_size );
}

File_link_pulldown.prototype.justify_image = function ( event, position ) {
  var image = getFirstElementByTagAndClassName( "img", null, this.link );
  if ( !image )
    return;

  removeElementClass( image, "left_justified" );
  removeElementClass( image, "center_justified" );
  removeElementClass( image, "right_justified" );
  addElementClass( image, position + "_justified" );

  this.update_position();
  this.editor.resize();
}

File_link_pulldown.prototype.update_position = function ( always_left_align ) {
  Pulldown.prototype.update_position.call( this, always_left_align );
}

File_link_pulldown.prototype.shutdown = function () {
  Pulldown.prototype.shutdown.call( this );

  disconnectAll( this.filename_field );
  if ( this.link )
    this.link.pulldown = null;

  disconnectAll( this.delete_button );
  disconnectAll( this.embed_checkbox );
  disconnectAll( this.left_justify_radio );
  disconnectAll( this.center_justify_radio );
  disconnectAll( this.right_justify_radio );
}


function Suggest_pulldown( wiki, notebook_id, invoker, anchor, relative_to, search_text, key_press_node ) {
  anchor.pulldown = this;
  this.anchor = anchor;
  this.previous_search_text = "";
  this.sequence_number = 0;

  Pulldown.call( this, wiki, notebook_id, "suggest_pulldown", anchor, relative_to );

  this.invoker = invoker;
  this.update_suggestions( search_text );

  var self = this;
  this.key_handler = connect( key_press_node, "onkeydown", function ( event ) { self.key_pressed( event ); } );

  Pulldown.prototype.update_position.call( this, true );
}

Suggest_pulldown.prototype = new function () { this.prototype = Pulldown.prototype; };
Suggest_pulldown.prototype.constructor = Suggest_pulldown;

Suggest_pulldown.prototype.update_suggestions = function ( search_text ) {
  // if the search text hasn't changed since last time, bail
  if ( this.previous_search_text == search_text )
    return;

  // if there is no search text, hide the pulldown and bail
  if ( !search_text ) {
    addElementClass( this.div, "invisible" );
    this.previous_search_text = "";
    return;
  }

  var self = this;
  this.previous_search_text = search_text;
  this.sequence_number += 1;
  var sequence_number = this.sequence_number;

  this.invoker.invoke( "/notebooks/search_titles", "GET", {
      "notebook_id": this.notebook_id,
      "search_text": search_text
    },
    function( result ) {
      // if the sequence number is not what we expect, then this must not be most recent suggests
      // update, so bail without displaying the result
      if ( self.sequence_number != sequence_number )
        return;

      self.display_suggestions( result, search_text );
    }
  );
}

Suggest_pulldown.prototype.display_suggestions = function ( result, search_text ) {
  if ( result.notes.length == 0 ) {
    addElementClass( this.div, "invisible" );
    return;
  }

  removeElementClass( this.div, "invisible" );
  var results_list = createDOM( "div" );
  var self = this;

  function connect_link( suggest_link, note ) {
    connect( suggest_link, "onclick", function ( event ) { self.suggestion_selected( event, note ); } );
  }

  for ( var i in result.notes ) {
    var note = result.notes[ i ];
    if ( !note.title ) continue;

    var suggest_link = createDOM( "a", { "href": "#", "class": "pulldown_link" } );
    suggest_link.innerHTML = note.summary;
    suggest_link.note = note;

    appendChildNodes( results_list, createDOM( "div", { "class": "suggestion" }, suggest_link ) );
    connect_link( suggest_link, note );
  }

  replaceChildNodes( this.div, results_list );
}

Suggest_pulldown.prototype.suggestion_selected = function ( event, note ) {
  event.stop();

  signal( this, "suggestion_selected", note );
}

Suggest_pulldown.prototype.key_pressed = function ( event ) {
  // an invisible Suggest_pulldown shouldn't grab keypresses
  if ( hasElementClass( this.div, "invisible" ) )
    return;

  var code = event.key().code;
  var selected = getFirstElementByTagAndClassName( "div", "selected_suggestion", this.div );

  // up arrow or shift-tab: move up to the previous suggestion
  if ( code == 38 || ( code == 9 && event.modifier().shift ) ) {
    this.previous_suggestion( selected );
  // down arrow or tab: move down to the previous suggestion
  } else if ( code == 40 || code == 9 ) {
    this.next_suggestion( selected );
  // enter: select current suggestion
  } else if ( code == 13 ) {
    var suggest_link = getFirstElementByTagAndClassName( "a", "pulldown_link", selected );

    if ( selected )
      this.suggestion_selected( event, suggest_link.note );
    else // if nothing is selected, don't handle enter
      return;
  // escape: hide the suggestions
  } else if ( code == 27 ) {
    addElementClass( this.div, "invisible" );
  // otherwise, not a key this method handles
  } else {
    return;
  }

  event.stop();
}

Suggest_pulldown.prototype.previous_suggestion = function ( selected ) {
  // if something is selected and there's a previous suggestion in the list, move the selection up
  if ( selected && selected.previousSibling ) {
    removeElementClass( selected, "selected_suggestion" );
    addElementClass( selected.previousSibling, "selected_suggestion" );
  // otherwise, hide the Suggest_pulldown
  } else {
    addElementClass( this.div, "invisible" );
  }
}

Suggest_pulldown.prototype.next_suggestion = function ( selected ) {
  // if something is selected and there's a next suggestion in the list, move the selection down
  if ( selected ) {
    if ( selected.nextSibling ) {
      removeElementClass( selected, "selected_suggestion" );
      addElementClass( selected.nextSibling, "selected_suggestion" );
    }
  // if nothing is selected yet, then just select the first link
  } else {
    var suggest_link = getFirstElementByTagAndClassName( "a", "pulldown_link", this.div );
    addElementClass( suggest_link.parentNode, "selected_suggestion" );
  }
}

Suggest_pulldown.prototype.update_position = function ( always_left_align ) {
  // ignore the requested always_left_align value and force it to true, since Suggest_pulldown
  // looks better that way
  Pulldown.prototype.update_position.call( this, true );
}

Suggest_pulldown.prototype.something_selected = function () {
  if ( hasElementClass( this.div, "invisible" ) )
    return false;

  var selected = getFirstElementByTagAndClassName( "div", "selected_suggestion", this.div );
  if ( selected )
    return true;

  return false;
}

Suggest_pulldown.prototype.visible = function () {
  return !hasElementClass( this.div, "invisible" );
}

Suggest_pulldown.prototype.shutdown = function () {
  Pulldown.prototype.shutdown.call( this );

  this.anchor.pulldown = null;
  disconnectAll( this );
  disconnect( this.key_handler );
}


function Font_pulldown( wiki, notebook_id, invoker, anchor, editor ) {
  anchor.pulldown = this;
  this.anchor = anchor;
  this.editor = editor;
  this.initial_selected_mark = null;

  Pulldown.call( this, wiki, notebook_id, "font_pulldown", anchor );

  this.invoker = invoker;

  var fonts = [
    [ "Arial", "arial,sans-serif" ],
    [ "Times New Roman", "times new roman,serif" ],
    [ "Courier", "courier new,monospace" ],
    [ "Comic Sans", "comic sans ms,sans-serif" ],
    [ "Garamond", "garamond,serif" ],
    [ "Georgia", "georgia,serif" ],
    [ "Tahoma", "tahoma,sans-serif" ],
    [ "Trebuchet", "trebuchet ms,sans-serif" ],
    [ "Verdana", "verdana,sans-serif" ]
  ];

  var self = this;
  var current_font_family = editor.query_command_value( "fontname" );
  if ( current_font_family ) {
    current_font_family = current_font_family.toLowerCase();
    current_font_family = current_font_family.replace( /'/g, "" ).replace( /-webkit-/, "" );
    current_font_family = current_font_family.split( ',' )[ 0 ];
  }

  for ( var i in fonts ) {
    var font = fonts[ i ];
    var font_name = font[ 0 ];
    var font_family = font[ 1 ];

    // using a button here instead of a <label> to make IE happy: when a <label> is used, clicking
    // on the label steals focus from the editor iframe and prevents the font from being changed
    var label = createDOM( "input", { "type": "button", "value": font_name, "class": "pulldown_label font_label_button", "style": "font-family: " + font_family + ";" } );

    var selected_mark_char = document.createTextNode( "\u25cf" );
    if ( current_font_family && font_family.search( current_font_family ) == 0 ) {
      var selected_mark = createDOM( "span", { "class": "selected_mark" }, selected_mark_char );
      this.initial_selected_mark = selected_mark;
    } else {
      var selected_mark = createDOM( "span", { "class": "selected_mark invisible" }, selected_mark_char );
    }

    var div = createDOM( "div", {}, selected_mark, " ", label );

    label.font_family = font_family;
    label.selected_mark = selected_mark;
    appendChildNodes( this.div, div );
    connect( label, "onclick", function ( event ) { self.font_name_clicked( event ); } );
  }

  Pulldown.prototype.finish_init.call( this );
}

Font_pulldown.prototype = new function () { this.prototype = Pulldown.prototype; };
Font_pulldown.prototype.constructor = Font_pulldown;

Font_pulldown.prototype.font_name_clicked = function ( event ) {
  var label = event.src();
  if ( this.initial_selected_mark )
    addElementClass( this.initial_selected_mark, "invisible" );
  removeElementClass( label.selected_mark, "invisible" );

  var self = this;
  setTimeout( function () {
    self.editor.focus();
    self.editor.exec_command( "fontname", label.font_family );
    self.shutdown();
  }, 100 );
}

Font_pulldown.prototype.shutdown = function () {
  Pulldown.prototype.shutdown.call( this );

  this.anchor.pulldown = null;
  disconnectAll( this );
}


function Note_tree( wiki, notebook_id, invoker ) {
  this.wiki = wiki;
  this.notebook_id = notebook_id;
  this.invoker = invoker;
  this.suggest_pulldown = null;

  // add onclick handlers to the initial note links within the tree
  var links = getElementsByTagAndClassName( "a", "note_tree_link", "note_tree_area" );

  var self = this;
  function connect_expander( note_id ) {
    connect( "note_tree_expander_" + note_id, "onclick", function ( event ) { self.expand_collapse_link( event, note_id ); } );
  }

  for ( var i in links ) {
    var link = links[ i ];
    var query = parse_query( link );
    var note_id = query[ "note_id" ];
    
    if ( note_id )
      connect_expander( note_id );

    connect( link, "onclick", function ( event ) { self.link_clicked( event ); } );
  }

  // connect to the wiki note events
  connect( wiki, "note_renamed", function ( editor, new_title ) { self.rename_link( editor, new_title ); } );
  connect( wiki, "note_added", function ( editor ) { self.add_root_link( editor.id, editor.title, editor.contents(), editor.startup ); } );
  connect( wiki, "note_removed", function ( id ) { self.remove_link( id ); } );
  connect( wiki, "note_saved", function ( editor ) { self.update_link( editor ); } );
}

Note_tree.prototype.link_clicked = function ( event ) {
  var link = event.target();
  var query = parse_query( link );
  var note_id = query[ "note_id" ];
  var title = query[ "title" ];

  if ( !note_id )
    return;

  this.wiki.load_editor( title, note_id );
  event.stop();
}

LINK_PATTERN = /<a\s+([^>]+\s)?href="[^"]+"[^>]*>/i;

Note_tree.prototype.add_root_link = function ( note_id, title, contents, startup ) {
  // for now, only add startup notes to the note tree
  if ( !startup )
    return;

  // if the root note is already present in the tree, no need to add it again
  var item = getElement( "note_tree_item_" + note_id );
  if ( item ) {
    new Highlight( item, { "endcolor": "#fafafa" } );
    return;
  }

  // display the tree expander arrow if the given note's contents contains any outgoing links
  if ( LINK_PATTERN.exec( contents ) )
    var expander = createDOM( "div", { "class": "tree_expander", "id": "note_tree_expander_" + note_id } );
  else
    var expander = createDOM( "div", { "class": "tree_expander_empty", "id": "note_tree_expander_" + note_id } );

  var link = createDOM( "a", {
   "href": "/notebooks/" + this.notebook_id + "?note_id=" + note_id,
   "id": "note_tree_link_" + note_id,
   "class": "note_tree_link"
  }, normalize_title( title ) );

  insertSiblingNodesBefore( "new_note_tree_link_row", createDOM(
    "tr",
    { "id": "note_tree_item_" + note_id, "class": "note_tree_item" },
    createDOM( "td", {}, expander ),
    createDOM( "td", {}, link )
  ) );

  var self = this;
  connect( expander, "onclick", function ( event ) { self.expand_collapse_link( event, note_id ); } );
  connect( link, "onclick", function ( event ) { self.link_clicked( event ); } );
}

Note_tree.prototype.remove_link = function ( note_id ) {
  var item = getElement( "note_tree_item_" + note_id );

  if ( item )
    removeElement( item );

  if ( getFirstElementByTagAndClassName( "a", null, "note_tree_root_table" ) )
    return;
}

Note_tree.prototype.rename_link = function ( editor, new_title ) {
  var link = getElement( "note_tree_link_" + editor.id );
  if ( link )
    replaceChildNodes( link, normalize_title( new_title ) );
}

Note_tree.prototype.update_link = function ( editor ) {
  var link = getElement( "note_tree_link_" + editor.id );

  if ( !link && editor.startup ) {
    this.add_root_link( editor.id, editor.title, editor.contents(), editor.startup );
    return;
  }

  if ( link && !editor.startup )
    this.remove_link( editor.id );

  // if the tree has any expanded links to the given editor's note, then update the children of
  // those links
  function update_links( note_tree, notebook_id, note_id, link, children_area ) {
    note_tree.invoker.invoke(
      "/notebooks/load_note_links", "GET", {
        "notebook_id": notebook_id,
        "note_id": note_id
      },
      function ( result ) { note_tree.display_child_links( result, link, children_area ); }
    );
  }

  var links = getElementsByTagAndClassName( "a", null, "note_tree_root_table" );

  for ( var i in links ) {
    var link = links[ i ]
    var note_id = parse_query( link )[ "note_id" ];
    var children_area = getFirstElementByTagAndClassName( "div", "note_tree_children_area", link.parentNode );

    if ( note_id != editor.id )
      continue;

    update_links( this, this.notebook_id, editor.id, link, children_area );
  }
}

Note_tree.prototype.expand_collapse_link = function ( event, note_id ) {
  var expander = event.target();

  if ( !expander || hasElementClass( expander, "tree_expander_empty" ) )
    return;

  // if it's collapsed, expand it
  if ( hasElementClass( expander, "tree_expander" ) ) {
    // first check if the expander is for a link to a parent/grandparent/etc. if so, just highlight
    // the containing table instead of performing an expansion
    var parent_node = expander.parentNode.parentNode;
    while ( !hasElementClass( parent_node, "note_tree_root_table" ) ) {
      parent_node = parent_node.parentNode;
      if ( !parent_node ) break;
      var parent_link = parent_node.previousSibling;

      if ( !parent_link || !hasElementClass( parent_link, "note_tree_link" ) ) continue;
      var parent_note_id = parse_query( parent_link )[ "note_id" ];

      if ( note_id == parent_note_id ) {
        new Highlight( parent_node.parentNode, { "endcolor": "#fafafa" } );
        return;
      }
    }

    var children_area = createDOM( "div", { "class": "note_tree_children_area" },
      createDOM( "span", { "class": "note_tree_loading" }, "loading..." )
    );

    swapElementClass( expander, "tree_expander", "tree_expander_expanded" );
    var link = getFirstElementByTagAndClassName( "a", null, expander.parentNode.parentNode );
    insertSiblingNodesAfter( link, children_area );

    var self = this;
    this.invoker.invoke(
      "/notebooks/load_note_links", "GET", {
        "notebook_id": this.notebook_id,
        "note_id": note_id
      },
      function ( result ) { self.display_child_links( result, link, children_area ); }
    );

    return;
  }

  // if it's expanded, collapse it
  if ( hasElementClass( expander, "tree_expander_expanded" ) ) {
    swapElementClass( expander, "tree_expander_expanded", "tree_expander" );
    var children = getFirstElementByTagAndClassName( "div", "note_tree_children_area", expander.parentNode.parentNode );
    if ( children )
      removeElement( children );
  }
}

Note_tree.prototype.display_child_links = function ( result, link, children_area ) {
  var self = this;

  function connect_expander( expander, note_id ) {
    connect( expander, "onclick", function ( event ) { self.expand_collapse_link( event, note_id ); } );
  }

  var span = createDOM( "span" );
  span.innerHTML = result.tree_html;

  // if there's a children area, replace its contents and add an onclick handler for each newly
  // loaded expander and each note link
  if ( children_area ) {
    replaceChildNodes( children_area, span );

    var child_links = getElementsByTagAndClassName( "a", null, children_area );
    for ( var i in child_links ) {
      var child_link = child_links[ i ];
      connect( child_link, "onclick", function ( event ) { self.link_clicked( event ); } );
      var expander = getFirstElementByTagAndClassName( "div", "tree_expander", child_link.parentNode.parentNode );

      if ( expander ) {
        var note_id = parse_query( child_link )[ "note_id" ];
        if ( note_id )
          connect_expander( expander, note_id );
      }
    }
  } else {
    var child_links = getElementsByTagAndClassName( "a", null, span );
  }

  // if the parent has no children anymore, remove its expander arrow
  if ( child_links.length == 0 ) {
    if ( children_area )
      removeElement( children_area );
    var expander = getFirstElementByTagAndClassName( "div", "tree_expander", link.parentNode.parentNode );
    if ( expander && link.parentNode.parentNode == expander.parentNode.parentNode ) {
      swapElementClass( expander, "tree_expander", "tree_expander_empty" );
      disconnectAll( expander );
      return;
    }

    expander = getFirstElementByTagAndClassName( "div", "tree_expander_expanded", link.parentNode.parentNode );
    if ( expander && link.parentNode.parentNode == expander.parentNode.parentNode ) {
      swapElementClass( expander, "tree_expander_expanded", "tree_expander_empty" );
      disconnectAll( expander );
      return
    }

    return;
  }

  // if a note without an expander arrow now has children, add an expander arrow for it
  var expander = getFirstElementByTagAndClassName( "div", "tree_expander_empty", link.parentNode.parentNode );
  if ( !expander || link.parentNode.parentNode != expander.parentNode.parentNode ) return;
  swapElementClass( expander, "tree_expander_empty", "tree_expander" );
  var note_id = parse_query( link )[ "note_id" ];
  disconnectAll( expander );
  connect_expander( expander, note_id );
}

Note_tree.prototype.move_link = function ( editor, position_after, position_before ) {
  var item = getElement( "note_tree_item_" + editor.id );

  if ( position_after ) {
    var after_item = getElement( "note_tree_item_" + position_after.id );
    insertSiblingNodesAfter( after_item, item );
  } else if ( position_before ) {
    var before_item = getElement( "note_tree_item_" + position_before.id );
    insertSiblingNodesBefore( before_item, item );
  }
}

Note_tree.prototype.start_link_add = function () {
  // if the add is already in progress, end the add instead of starting one
  var new_note_tree_link_field = getElement( "new_note_tree_link_field" );
  if ( new_note_tree_link_field ) {
    this.end_link_add();
    return; 
  }

  link_field = createDOM(
    "input", {
      "type": "text",
      "value": "",
      "id": "new_note_tree_link_field",
      "name": "new_note_tree_link_field",
      "title": "Enter the title of an existing note.",
      "size": "10",
      "autocomplete": "off",
      "class": "text_field"
    }
  );

  var ok_button = createDOM(
    "input", {
      "type": "button",
      "class": "message_button",
      "value": "add",
      "title": "add the note"
    }
  );

  var form = createDOM(
    "form", { "id": "new_note_tree_link_form", "class": "inline" }, link_field, ok_button
  );

  replaceChildNodes( "new_note_tree_link_area", form );

  // add a suggest pulldown beneath the link name text field
  var self = this;
  this.suggest_pulldown = new Suggest_pulldown(
    this.wiki, this.notebook_id, this.invoker, link_field, null, "", link_field
  );
  connect( this.suggest_pulldown, "suggestion_selected", function ( note ) {
    self.end_link_add( note );
  } );
  
  connect( form, "onsubmit", function ( event ) {
    self.end_link_add();
    event.stop();
  } );
  connect( form, "onkeyup", function ( event ) {
    self.suggest_pulldown.update_suggestions( link_field.value );
  } );
  connect( ok_button, "onclick", function ( event ) {
    self.end_link_add();
    event.stop();
  } );

  link_field.focus();
  link_field.select();
}

Note_tree.prototype.end_link_add = function ( note ) {
  // if no note is provided, load it based on the title
  if ( !note ) {
    var note_name = getElement( "new_note_tree_link_field" ).value;
    replaceChildNodes( "new_note_tree_link_area", "" );

    // if the new name is blank, bail
    if ( /^\s*$/.test( note_name ) )
      return;

    // load the requested note by title and add it as a root link
    var self = this;
    this.invoker.invoke( "/notebooks/load_note_by_title", "GET", {
      "notebook_id": this.notebook_id,
      "note_title": note_name
    }, function ( result ) {
      self.save_and_display_startup_note( result.note );
    } );
  // otherwise, a note is provided
  } else {
    replaceChildNodes( "new_note_tree_link_area", "" );
    this.save_and_display_startup_note( note );
  }

  if ( this.suggest_pulldown ) {
    this.suggest_pulldown.shutdown();
    this.suggest_pulldown = null;
  }
}

Note_tree.prototype.save_and_display_startup_note = function ( note ) {
  if ( !note ) {
    this.wiki.display_message( "Sorry, a note by that title doesn't exist. (If you're trying to create a new note, then simply click that large \"+\" button on the left.)" );
    return;
  }

  // if it's already a startup note, just highlight it and bail
  if ( note.startup ) {
    this.add_root_link( note.object_id, note.title, note.contents, true );
    return;
  }

  // mark the note as a startup note on the client
  this.wiki.startup_notes[ note.object_id ] = true;
  var editor = editor_by_id( note.object_id );
  if ( editor )
    editor.startup = true;

  // save the note as a startup note on the server, and then add it to the note tree
  var self = this;
  this.invoker.invoke( "/notebooks/save_note", "POST", {
    "notebook_id": this.notebook_id,
    "note_id": note.object_id,
    "contents": note.contents,
    "startup": true,
    "previous_revision": note.revision
  }, function ( result ) {
    self.add_root_link( note.object_id, note.title, note.contents, true );
  } );
}


function Recent_notes( wiki, notebook_id, invoker ) {
  this.wiki = wiki;
  this.notebook_id = notebook_id;
  this.invoker = invoker;

  this.INCREMENT = 10;
  this.max_recent_notes_count = this.INCREMENT; // maximum increases when the user clicks "more"
  this.total_notes_count = 0;
  this.total_notes_count_updated( wiki.total_notes_count );

  // if there's no recent notes table, there's nothing to do with recent notes!
  if ( !getElement( "recent_notes_table" ) )
    return;

  // add onclick handlers to the recent note links as well
  var self = this;
  var recent_links = getElementsByTagAndClassName( "a", "recent_note_link", "note_tree_area" );

  for ( var i in recent_links ) {
    var link = recent_links[ i ];
    var query = parse_query( link );
    var note_id = query[ "note_id" ];

    connect( link, "onclick", function ( event ) { self.link_clicked( event ); } );
  }

  // connect to the wiki note events
  connect( wiki, "note_added", function ( editor ) { self.add_link( editor ); } );
  connect( wiki, "note_removed", function ( id ) { self.remove_link( id ); } );
  connect( wiki, "note_saved", function ( editor ) { self.update_link( editor ); } );
  connect( wiki, "total_notes_count_updated", function ( count ) { self.total_notes_count_updated( count ); } );

  // connect to the "more" navigation link
  connect( "recent_notes_more_link", "onclick", function ( event ) { self.more_clicked( event ); } );
  connect( "recent_notes_less_link", "onclick", function ( event ) { self.less_clicked( event ); } );
}

Recent_notes.prototype.links_count = function () {
  var recent_links = getElementsByTagAndClassName( "a", "recent_note_link", "note_tree_area" );
  return recent_links.length;
}

Recent_notes.prototype.total_notes_count_updated = function( count ) {
  this.total_notes_count = count;
  this.update_navigation_links();
}

Recent_notes.prototype.update_navigation_links = function() {
  var more_link = getElement( "recent_notes_more_link" );
  if ( more_link ) {
    if ( this.total_notes_count > this.max_recent_notes_count )
      removeElementClass( more_link, "undisplayed" );
    else
      addElementClass( more_link, "undisplayed" );
  }

  var less_link = getElement( "recent_notes_less_link" );
  if ( less_link ) {
    if ( this.max_recent_notes_count > this.INCREMENT )
      removeElementClass( less_link, "undisplayed" );
    else
      addElementClass( less_link, "undisplayed" );
  }
}

Recent_notes.prototype.link_clicked = function ( event ) {
  var link = event.target();
  var query = parse_query( link );
  var note_id = query[ "note_id" ];
  var title = query[ "title" ];

  if ( !note_id )
    return;

  this.wiki.load_editor( title, note_id );
  event.stop();
}

Recent_notes.prototype.more_clicked = function ( event ) {
  event.stop();
  this.max_recent_notes_count += this.INCREMENT;

  var self = this;
  var links_count = this.links_count();

  this.invoker.invoke(
    "/notebooks/load_recent_updates", "GET", {
      "notebook_id": this.notebook_id,
      "start": links_count,
      "count": this.max_recent_notes_count - links_count
    },
    function ( result ) { self.append_links( result ); }
  );
}

Recent_notes.prototype.append_links = function ( result ) {
  var self = this;
  var table = getElement( "recent_notes_table" );
  var links_count = this.links_count();

  for ( var i in result.notes ) {
    var note = result.notes[ i ];
    var row = table.insertRow( links_count + 1 );
    row.setAttribute( "id", "recent_note_item_" + note.object_id );
    addElementClass( row, "recent_note_item" );

    var expander_td = row.insertCell( 0 );
    expander_td.innerHTML = '<div id="recent_note_expander_' + note.object_id + '" class="tree_expander_empty"';
    var link_td = row.insertCell( 1 );
    link_td.innerHTML =
      '<a href="/notebooks/' + this.notebook_id + '?note_id=' + note.object_id +
      '" id="recent_note_link_' + note.object_id + '" class="recent_note_link">' +
      ( normalize_title( note.title ) ) + '</a>';

    connect( "recent_note_link_" + note.object_id, "onclick", function ( event ) { self.link_clicked( event ); } );

    links_count += 1;
  }

  this.update_navigation_links();
}

Recent_notes.prototype.less_clicked = function ( event ) {
  event.stop();
  this.max_recent_notes_count -= this.INCREMENT;
  
  var rows_to_remove_count = this.links_count() - this.max_recent_notes_count;
  if ( rows_to_remove_count <= 0 )
    return;

  var rows = getElementsByTagAndClassName( "tr", "recent_note_item", "recent_notes_table" );
  var row_count = rows.length;

  for ( var i = 0; i < rows_to_remove_count; ++i ) {
    removeElement( rows[ row_count - i - 1 ] );
  }

  this.update_navigation_links();
}

Recent_notes.prototype.add_link = function ( editor ) {
  // if the link is already present in the recent notes list, bail
  var item = getElement( "recent_note_item_" + editor.id )
  if ( item ) return;

  // if there will be too many recent notes listed once another is added, then remove the last one
  var recent_items = getElementsByTagAndClassName( "tr", "recent_note_item", "recent_notes_table" );
  if ( recent_items && recent_items.length >= this.max_recent_notes_count ) {
    var last_item = recent_items[ recent_items.length - 1 ];
    removeElement( last_item );
  }

  // add a new recent note link at the top of the list
  var expander = createDOM( "div", { "class": "tree_expander_empty", "id": "recent_note_expander_" + editor.id } );

  var link = createDOM( "a", {
   "href": "/notebooks/" + this.notebook_id + "?note_id=" + editor.id,
   "id": "recent_note_link_" + editor.id,
   "class": "recent_note_link"
  }, normalize_title( editor.title ) );

  insertSiblingNodesAfter( "recent_notes_top", createDOM(
    "tr",
    { "id": "recent_note_item_" + editor.id, "class": "recent_note_item" },
    createDOM( "td", {}, expander ),
    createDOM( "td", {}, link )
  ) );

  var self = this;
  connect( link, "onclick", function ( event ) { self.link_clicked( event ); } );
}

Recent_notes.prototype.remove_link = function ( note_id ) {
  var item = getElement( "recent_note_item_" + note_id );
  if ( !item ) return;

  removeElement( item );
}

Recent_notes.prototype.update_link = function ( editor ) {
  var item = getElement( "recent_note_item_" + editor.id );
  var link = getElement( "recent_note_link_" + editor.id );

  // the link isn't in the recent notes list, so add it
  if ( !item || !link ) {
    this.add_link( editor );
    return;
  }

  // the link is already in the recent notes list, so just move it to the top of the list
  removeElement( item );
  replaceChildNodes( link, normalize_title( editor.title ) );
  insertSiblingNodesAfter( "recent_notes_top", item );
}

function Autosaver( wiki ) {
  this.wiki = wiki;
  this.last_state_change_time = null;
  this.timer = null;
  var INTERVAL_MILLISECONDS = 10000; // 10 seconds

  function save_if_idle() {
    // if the note state has changed in the last few seconds (e.g. due to typing), don't save,
    // but do reschedule a new timer
    if ( this.last_state_change_time + INTERVAL_MILLISECONDS > ( new Date() ).getTime() ) {
      if ( this.timer ) clearTimeout( this.timer );
      this.timer = setTimeout( save_if_idle, INTERVAL_MILLISECONDS );
      return;
    }

    this.wiki.save_editor();
  }

  // whenever the focused editor's state changes, record the current time, cancel any current
  // timer, and schedule a timer to save the editor in several seconds from now
  var self = this;
  connect( wiki, "note_state_changed", function ( editor ) {
    self.last_state_change_time = ( new Date() ).getTime();

    if ( self.timer ) clearTimeout( self.timer );
    self.timer = setTimeout( save_if_idle, INTERVAL_MILLISECONDS );
  } );
}
