function Wiki( invoker ) {
  this.next_id = null;
  this.focused_editor = null;
  this.blank_editor_id = null;
  this.notebook = null;
  this.notebook_id = getElement( "notebook_id" ).value;
  this.parent_id = getElement( "parent_id" ).value; // id of the notebook containing this one
  this.startup_notes = new Array();  // map of startup notes: note id to bool
  this.open_editors = new Array();   // map of open notes: note title to editor
  this.all_notes_editor = null;      // editor for display of list of all notes
  this.search_results_editor = null; // editor for display of search results
  this.invoker = invoker;
  this.rate_plan = evalJSON( getElement( "rate_plan" ).value );
  this.storage_usage_high = false;

  var total_notes_count_node = getElement( "total_notes_count" );
  if ( total_notes_count_node )
    this.total_notes_count = parseInt( scrapeText( total_notes_count_node ) );
  else
    this.total_notes_count = null;

  // grab the current notebook from the list of available notebooks
  var notebooks = evalJSON( getElement( "notebooks" ).value );
  for ( var i in notebooks ) {
    if ( notebooks[ i ].object_id == this.notebook_id ) {
      this.notebook = notebooks[ i ]
      break;
    }
  }

  if ( this.notebook && this.notebook.read_write ) {
    unsupported_agent = null;
    if ( /Safari/.test( navigator.userAgent ) )
      unsupported_agent = "Safari";
    if ( /Opera/.test( navigator.userAgent ) )
      unsupported_agent = "Opera";

    if ( unsupported_agent )
      alert( "Luminotes does not currently support the " + unsupported_agent + " web browser for editing. If possible, please use Firefox or Internet Explorer instead. " + unsupported_agent + " support will be added in a future release. Sorry for the inconvenience." );
  }

  // populate the wiki with startup notes
  this.populate(
    evalJSON( getElement( "startup_notes" ).value || "null" ),
    evalJSON( getElement( "current_notes" ).value || "null" ),
    evalJSON( getElement( "note_read_write" ).value || "true" )
  );

  this.display_storage_usage( evalJSON( getElement( "storage_bytes" ).value || "0" ) );

  connect( this.invoker, "error_message", this, "display_error" );
  connect( this.invoker, "message", this, "display_message" );
  connect( "search_form", "onsubmit", this, "search" );
  connect( "html", "onclick", this, "background_clicked" );
  connect( "html", "onkeydown", this, "key_pressed" );

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
  var logout_link = getElement( "logout_link" );
  if ( logout_link ) {
    connect( "logout_link", "onclick", function ( event ) {
      self.save_editor( null, true );
      self.invoker.invoke( "/users/logout", "POST" );
      event.stop();
    } );
  }
}

Wiki.prototype.update_next_id = function ( result ) {
  this.next_id = result.next_id;
}

Wiki.prototype.display_storage_usage = function( storage_bytes ) {
  if ( !storage_bytes )
    return;

  // display the user's current storage usage
  var MEGABYTE = 1024 * 1024;
  function bytes_to_megabytes( storage_bytes ) {
    return Math.round( storage_bytes / MEGABYTE );
  }

  var quota_bytes = this.rate_plan.storage_quota_bytes;
  if ( !quota_bytes )
    return;

  var usage_percent = Math.round( storage_bytes / quota_bytes * 100.0 );

  if ( usage_percent > 90 ) {
    var storage_usage_class = "storage_usage_high";
    if ( this.storage_usage_high == false )
      this.display_message( "You are currently using " + usage_percent + "% of your available storage space. Please delete some notes, empty the trash, or upgrade your account." );
    this.storage_usage_high = true;
  } else if ( usage_percent > 75 ) {
    var storage_usage_class = "storage_usage_medium";
    this.storage_usage_high = false;
  } else {
    var storage_usage_class = "storage_usage_low";
    this.storage_usage_high = false;
  }

  replaceChildNodes(
    "storage_usage_area",
    createDOM( "div", { "class": storage_usage_class },
    bytes_to_megabytes( storage_bytes ) + " MB (" + usage_percent + "%) of " + bytes_to_megabytes( quota_bytes ) + " MB" )
  );
}

Wiki.prototype.populate = function ( startup_notes, current_notes, note_read_write ) {
  // create an editor for each startup note in the received notebook, focusing the first one
  var focus = true;
  for ( var i in startup_notes ) {
    var startup_note = startup_notes[ i ];
    this.startup_notes[ startup_note.object_id ] = true;

    // don't actually create an editor if a particular list of notes was provided in the result
    if ( current_notes.length == 0 ) {
      var editor = this.create_editor(
        startup_note.object_id,
        // grab this note's contents from the static notes area
        getElement( "static_note_" + startup_note.object_id ).innerHTML,
        startup_note.deleted_from_id,
        startup_note.revision,
        startup_note.creation,
        this.notebook.read_write, false, focus
      );

      this.open_editors[ startup_note.title ] = editor;
      focus = false;
    }
  }

  // if particular notes were provided, then display editors for them
  var focus = true;
  for ( var i in current_notes ) {
    var note = current_notes[ i ];

    this.create_editor(
      note.object_id,
      getElement( "static_note_" + note.object_id ).innerHTML,
      note.deleted_from_id,
      note.revision,
      note.creation,
      this.notebook.read_write && note_read_write, false, focus
    );
    focus = false;
  }

  if ( startup_notes.length == 0 && current_notes.length == 0 )
    this.display_empty_message();

  var self = this;

  var empty_trash_link = getElement( "empty_trash_link" );
  if ( empty_trash_link )
    connect( empty_trash_link, "onclick", function ( event ) { self.delete_all_editors( event ); } );

  if ( this.notebook.read_write ) {
    connect( window, "onunload", function ( event ) { self.editor_focused( null, true ); } );
    connect( "newNote", "onclick", this, "create_blank_editor" );
    connect( "createLink", "onclick", this, "toggle_link_button" );
    connect( "bold", "onclick", function ( event ) { self.toggle_button( event, "bold" ); } );
    connect( "italic", "onclick", function ( event ) { self.toggle_button( event, "italic" ); } );
    connect( "underline", "onclick", function ( event ) { self.toggle_button( event, "underline" ); } );
    connect( "title", "onclick", function ( event ) { self.toggle_button( event, "title", "h3" ); } );
    connect( "insertUnorderedList", "onclick", function ( event ) { self.toggle_button( event, "insertUnorderedList" ); } );
    connect( "insertOrderedList", "onclick", function ( event ) { self.toggle_button( event, "insertOrderedList" ); } );

    this.make_image_button( "newNote", "new_note", true );
    this.make_image_button( "createLink", "link" );
    this.make_image_button( "bold" );
    this.make_image_button( "italic" );
    this.make_image_button( "underline" );
    this.make_image_button( "title" );
    this.make_image_button( "insertUnorderedList", "bullet_list" );
    this.make_image_button( "insertOrderedList", "numbered_list" );

    // grab the next available object id
    this.invoker.invoke( "/next_id", "POST", null,
      function( result ) { self.update_next_id( result ); }
    );
  }

  var all_notes_link = getElement( "all_notes_link" );
  if ( all_notes_link ) {
    connect( all_notes_link, "onclick", function ( event ) {
      self.load_editor( "all notes", "null", null, null, getElement( "notes_top" ) );
      event.stop();
    } );
  }

  var download_html_link = getElement( "download_html_link" );
  if ( download_html_link ) {
    connect( download_html_link, "onclick", function ( event ) {
      self.save_editor( null, true );
    } );
  }

  var add_notebook_link = getElement( "add_notebook_link" );
  if ( add_notebook_link ) {
    connect( add_notebook_link, "onclick", function ( event ) {
      self.invoker.invoke( "/notebooks/create", "POST" );
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
}

Wiki.prototype.background_clicked = function ( event ) {
  if ( !hasElementClass( event.target(), "pulldown_checkbox" ) )
    this.clear_pulldowns();
}

Wiki.prototype.create_blank_editor = function ( event ) {
  if ( event ) event.stop();

  this.clear_messages();
  this.clear_pulldowns();

  // if we're within the trash, don't allow new note creation
  if ( this.notebook.name == "trash" ) {
    this.display_error( "You can't create notes in the trash." );
    return;
  }

  // if there is already a blank editor, then highlight it and bail
  if ( this.blank_editor_id != null ) {
    var blank_iframe_id = "note_" + this.blank_editor_id;
    var iframe = getElement( blank_iframe_id );
    if ( iframe && iframe.editor.empty() ) {
      iframe.editor.highlight();
      return;
    }
  }

  var editor = this.create_editor( undefined, undefined, undefined, undefined, undefined, this.notebook.read_write, true, true );
  this.increment_total_notes_count();
  this.blank_editor_id = editor.id;

  this.add_all_notes_link( editor.id, "" );
}

Wiki.prototype.load_editor = function ( note_title, note_id, revision, link, position_after ) {
  if ( this.notebook.name == "trash" && !revision ) {
    this.display_message( "If you'd like to use this note, try undeleting it first.", undefined, position_after );
    return;
  }

  // if a link is given with an open link pulldown, then ignore the note title given and use the
  // one from the pulldown instead
  if ( link ) {
    var pulldown = link.pulldown;
    var pulldown_title = undefined;
    if ( pulldown ) {
      pulldown_title = strip( pulldown.title_field.value );
      if ( pulldown_title )
        note_title = pulldown_title;
    }

    // if the title looks like a URL, then make it a link to an external site
    if ( /^\w+:\/\//.test( note_title ) ) {
      link.target = "_new";
      link.href = note_title;
      window.open( link.href );
      return
    }
    if ( link.target )
      link.removeAttribute( "target" );
  }

  // if the note corresponding to the link's id is already open, highlight it and bail, but only if
  // we didn't pull a title from an open link pulldown
  if ( !pulldown_title ) {
    if ( revision )
      var iframe = getElement( "note_" + note_id + " " + revision );
    else
      var iframe = getElement( "note_" + note_id );

    if ( iframe ) {
      iframe.editor.highlight();
      if ( link )
        link.href = "/notebooks/" + this.notebook_id + "?note_id=" + note_id;
      return;
    }
  }

  // if there's not a valid destination note id, then load by title instead of by id
  var self = this;
  if ( pulldown_title || note_id == undefined || note_id == "new" || note_id == "null" ) {
    // if the note_title corresponds to a "magic" note's title, then dynamically highlight or create the note
    if ( note_title == "all notes" ) {
      this.invoker.invoke(
        "/notebooks/all_notes", "GET", { "notebook_id": this.notebook.object_id },
        function( result ) { self.display_all_notes_list( result ); }
      );
      return;
    }
    if ( note_title == "search results" ) {
      var editor = this.open_editors[ note_title ];
      if ( editor ) {
        editor.highlight();
        return;
      }

      this.display_search_results();
      return;
    }

    // but if the note corresponding to the link's title is already open, highlight it and bail
    if ( !revision ) {
      var editor = this.open_editors[ note_title ];
      if ( editor ) {
        editor.highlight();
        if ( link )
          link.href = "/notebooks/" + this.notebook_id + "?note_id=" + editor.id;
        return;
      }
    }

    this.invoker.invoke(
      "/notebooks/load_note_by_title", "GET", {
        "notebook_id": this.notebook_id,
        "note_title": note_title,
        "revision": revision
      },
      function ( result ) { self.parse_loaded_editor( result, note_title, revision, link, position_after ); }
    );
    return;
  }

  this.invoker.invoke(
    "/notebooks/load_note", "GET", {
      "notebook_id": this.notebook_id,
      "note_id": note_id,
      "revision": revision
    },
    function ( result ) { self.parse_loaded_editor( result, note_title, revision, link, position_after ); }
  );
}

Wiki.prototype.resolve_link = function ( note_title, link, callback ) {
  // if the title looks like a URL, then make it a link to an external site
  if ( /^\w+:\/\//.test( note_title ) ) {
    link.target = "_new";
    link.href = note_title;
    if ( callback ) callback( "web link" );
    return;
  }
  if ( link && link.target )
    link.removeAttribute( "target" );

  if ( note_title == "all notes" || note_title == "search results" ) {
    link.href = "/notebooks/" + this.notebook_id + "?" + queryString(
      [ "title", "note_id" ],
      [ note_title, "null" ]
    );
    if ( callback ) {
      if ( note_title == "all notes" )
        callback( "list of all notes in this notebook" );
      else
        callback( "current search results" );
    }
    return;
  }

  var id = parse_query( link ).note_id;

  // if the link already has a valid-looking id, it's already resolved, so bail
  if ( !callback && id != undefined && id != "new" && id != "null" )
    return;

  if ( note_title.length == 0 )
    return;

  // if the note corresponding to the link's title is already open, resolve the link and bail
  var editor = this.open_editors[ note_title ];
  if ( editor ) {
    if ( link )
      link.href = "/notebooks/" + this.notebook_id + "?note_id=" + editor.id;
    if ( callback )
      callback( editor.contents() );
    return;
  }

  var self = this;
  this.invoker.invoke(
    "/notebooks/" + ( callback ? "load_note_by_title" : "lookup_note_id" ), "GET", {
      "notebook_id": this.notebook_id,
      "note_title": note_title
    },
    function ( result ) {
      if ( result && ( result.note || result.note_id ) ) {
        link.href = "/notebooks/" + self.notebook_id + "?note_id=" + ( result.note ? result.note.object_id : result.note_id );
      } else {
        link.href = "/notebooks/" + self.notebook_id + "?" + queryString(
          [ "title", "note_id" ],
          [ note_title, "null" ]
        );
      }
      if ( callback )
        callback( ( result && result.note ) ? result.note.contents : null );
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
  } else {
    var id = null;
    var note_text = "<h3>" + note_title;
    var deleted_from_id = null;
    var actual_revision = null;
    var actual_creation = null;
    this.increment_total_notes_count();
  }

  if ( requested_revision )
    var read_write = false; // show previous revisions as read-only
  else
    var read_write = this.notebook.read_write;

  var editor = this.create_editor( id, note_text, deleted_from_id, actual_revision, actual_creation, read_write, true, false, position_after );
  id = editor.id;

  // if a link that launched this editor was provided, update it with the created note's id
  if ( link && id )
    link.href = "/notebooks/" + this.notebook_id + "?note_id=" + id;
}

Wiki.prototype.create_editor = function ( id, note_text, deleted_from_id, revision, creation, read_write, highlight, focus, position_after ) {
  var self = this;
  if ( isUndefinedOrNull( id ) ) {
    if ( this.notebook.read_write ) {
      id = this.next_id;
      this.invoker.invoke( "/next_id", "POST", null,
        function( result ) { self.update_next_id( result ); }
      );
    } else {
      id = 0;
    }
  }

  // for read-only notes within read-write notebooks, tack the revision timestamp onto the start of the note text
  if ( !read_write && this.notebook.read_write && revision ) {
    var short_revision = this.brief_revision( revision );
    note_text = "<p>Previous revision from " + short_revision + "</p>" + note_text;
  }

  if ( !read_write && creation ) {
    var short_creation = this.brief_revision( creation );
    note_text = '<p>' + short_creation + ' | <a href="/blog?note_id=' + id + '" target="_top">permalink</a></p>' + note_text;
  }

  var startup = this.startup_notes[ id ];
  var editor = new Editor( id, this.notebook_id, note_text, deleted_from_id, revision, read_write, startup, highlight, focus, position_after );

  if ( this.notebook.read_write ) {
    connect( editor, "state_changed", this, "editor_state_changed" );
    connect( editor, "title_changed", this, "editor_title_changed" );
    connect( editor, "key_pressed", this, "editor_key_pressed" );
    connect( editor, "delete_clicked", function ( event ) { self.delete_editor( event, editor ) } );
    connect( editor, "undelete_clicked", function ( event ) { self.undelete_editor_via_trash( event, editor ) } );
    connect( editor, "changes_clicked", function ( event ) { self.toggle_editor_changes( event, editor ) } );
    connect( editor, "options_clicked", function ( event ) { self.toggle_editor_options( event, editor ) } );
    connect( editor, "focused", this, "editor_focused" );
  }

  connect( editor, "load_editor", this, "load_editor" );
  connect( editor, "resolve_link", this, "resolve_link" );
  connect( editor, "hide_clicked", function ( event ) { self.hide_editor( event, editor ) } );
  connect( editor, "submit_form", function ( url, form ) {
    self.invoker.invoke( url, "POST", null, null, form );
  } );

  this.clear_messages();
  this.clear_pulldowns();

  return editor;
}

Wiki.prototype.editor_state_changed = function ( editor ) {
  this.update_toolbar();
  this.display_link_pulldown( editor );
}

Wiki.prototype.editor_title_changed = function ( editor, old_title, new_title ) {
  delete this.open_editors[ old_title ];

  if ( new_title != null && !editor.empty() ) {
    this.open_editors[ new_title ] = editor;
    this.add_all_notes_link( editor.id, new_title );
  }
}

Wiki.prototype.display_link_pulldown = function ( editor, link ) {
  if ( !editor.read_write ) {
    this.clear_pulldowns();
    return;
  }

  if ( !link )
    link = editor.find_link_at_cursor();

  // if there's no link at the current cursor location, or there is a link but it was just started,
  // bail
  if ( !link || link == editor.link_started ) {
    this.clear_pulldowns();
    return;
  }

  var pulldown = link.pulldown;
  if ( pulldown )
    pulldown.update_position();

  // if the cursor is now on a link, display a link pulldown if there isn't already one open
  if ( link_title( link ).length > 0 ) {
    if ( !pulldown ) {
      this.clear_pulldowns();
      new Link_pulldown( this, this.notebook_id, this.invoker, editor, link );
    }
  }
}

Wiki.prototype.editor_focused = function ( editor, fire_and_forget ) {
  if ( editor )
    addElementClass( editor.iframe, "focused_note_frame" );

  if ( this.focused_editor && this.focused_editor != editor ) {
    this.clear_pulldowns();
    removeElementClass( this.focused_editor.iframe, "focused_note_frame" );

    // if the formerly focused editor is completely empty, then remove it as the user leaves it and switches to this editor
    if ( this.focused_editor.id == this.blank_editor_id && this.focused_editor.empty() ) {
      this.remove_all_notes_link( this.focused_editor.id );
      this.focused_editor.shutdown();
      this.decrement_total_notes_count();
      this.display_empty_message();
    } else {
      // when switching editors, save the one being left
      this.save_editor( null, fire_and_forget );
    }
  }

  this.focused_editor = editor;
}

Wiki.prototype.key_pressed = function ( event ) {
  if ( !this.notebook.read_write )
    return;

  var code = event.key().code;
  if ( event.modifier().ctrl ) {
    // ctrl-n: new note
    if ( code == 78 )
      this.create_blank_editor( event );
  }
}

Wiki.prototype.editor_key_pressed = function ( editor, event ) {
  var code = event.key().code;
  if ( event.modifier().ctrl ) {
    // ctrl-backtick: alert with frame HTML contents (temporary for debugging)
    if ( code == 192 || code == 96 ) {
      alert( editor.contents() );
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
    // ctrl-t: title
    } else if ( code == 84 ) {
      this.toggle_button( event, "title", "h3" );
    // ctrl-period: unordered list
    } else if ( code == 190 ) {
      this.toggle_button( event, "insertUnorderedList" );
    // ctrl-1: ordered list
    } else if ( code == 49 ) {
      this.toggle_button( event, "insertOrderedList" );
    // ctrl-l: link
    } else if ( code == 76 ) {
      this.toggle_link_button( event );
    // ctrl-n: new note
    } else if ( code == 78 ) {
      this.create_blank_editor( event );
    // ctrl-h: hide note
    } else if ( code == 72 ) {
      if ( !editor.deleted_from_id )
        this.hide_editor( event );
    // ctrl-d: delete note
    } else if ( code == 68 ) {
      this.delete_editor( event );
    }
  // IE: hitting space or tab while making a link shouldn't end the link
  } else if ( ( code == 32 || code == 9 ) && editor.document.selection && editor.state_enabled( "createLink" ) ) {
    var range = editor.document.selection.createRange();
    var text = range.parentElement().firstChild;
    text.nodeValue += " ";
    event.stop();
  }
}

IMAGE_DIR = "/static/images/";

Wiki.prototype.make_image_button = function ( name, filename_prefix, handle_mouse_up_and_down ) {
  var button = getElement( name );

  if ( !filename_prefix )
    filename_prefix = name;

  button.filename_prefix = filename_prefix;

  connect( button, "onmouseover", function ( event ) {
    if ( /_down/.test( button.src ) )
      button.src = IMAGE_DIR + filename_prefix + "_button_down_hover.png";
    else
      button.src = IMAGE_DIR + filename_prefix + "_button_hover.png";
  } );

  connect( button, "onmouseout", function ( event ) {
    if ( /_down/.test( button.src ) )
      button.src = IMAGE_DIR + filename_prefix + "_button_down.png";
    else
      button.src = IMAGE_DIR + filename_prefix + "_button.png";
  } );

  if ( handle_mouse_up_and_down ) {
    connect( button, "onmousedown", function ( event ) {
      if ( /_hover/.test( button.src ) )
        button.src = IMAGE_DIR + filename_prefix + "_button_down_hover.png";
      else
        button.src = IMAGE_DIR + filename_prefix + "_button_down.png";
    } );
    connect( button, "onmouseup", function ( event ) {
      if ( /_hover/.test( button.src ) )
        button.src = IMAGE_DIR + filename_prefix + "_button_hover.png";
      else
        button.src = IMAGE_DIR + filename_prefix + "_button.png";
    } );
  }
}

Wiki.prototype.down_image_button = function ( name ) {
  var button = getElement( name );

  if ( /_down/.test( button.src ) )
    return;

  if ( /_hover/.test( button.src ) )
    button.src = IMAGE_DIR + button.filename_prefix + "_button_down_hover.png";
  else
    button.src = IMAGE_DIR + button.filename_prefix + "_button_down.png";
}

Wiki.prototype.up_image_button = function ( name ) {
  var button = getElement( name );

  if ( !/_down/.test( button.src ) )
    return;

  if ( /_hover/.test( button.src ) )
    button.src = IMAGE_DIR + button.filename_prefix + "_button_hover.png";
  else
    button.src = IMAGE_DIR + button.filename_prefix + "_button.png";
}

Wiki.prototype.toggle_image_button = function ( name ) {
  var button = getElement( name );

  if ( /_down/.test( button.src ) ) {
    if ( /_hover/.test( button.src ) )
      button.src = IMAGE_DIR + button.filename_prefix + "_button_hover.png";
    else
      button.src = IMAGE_DIR + button.filename_prefix + "_button.png";
    return false;
  } else {
    if ( /_hover/.test( button.src ) )
      button.src = IMAGE_DIR + button.filename_prefix + "_button_down_hover.png";
    else
      button.src = IMAGE_DIR + button.filename_prefix + "_button_down.png";
    return true;
  }
}

Wiki.prototype.toggle_button = function ( event, button_id, state_name ) {
  this.clear_messages();
  this.clear_pulldowns();

  if ( this.focused_editor && this.focused_editor.read_write ) {
    this.focused_editor.focus();
    this.focused_editor.exec_command( state_name || button_id );
    this.focused_editor.resize();
    this.update_button( button_id, state_name );
  }

  event.stop();
}

Wiki.prototype.update_button = function ( button_id, state_name ) {
  if ( this.focused_editor.state_enabled( state_name || button_id ) )
    this.down_image_button( button_id );
  else
    this.up_image_button( button_id );
}

Wiki.prototype.update_toolbar = function() {
  if ( this.focused_editor ) {
    this.update_button( "bold" );
    this.update_button( "italic" );
    this.update_button( "underline" );
    this.update_button( "title", "h3" );
    this.update_button( "insertUnorderedList" );
    this.update_button( "insertOrderedList" );
    this.update_button( "createLink" );
  }
}

Wiki.prototype.toggle_link_button = function ( event ) {
  this.clear_messages();
  this.clear_pulldowns();
  var link = null;

  if ( this.focused_editor && this.focused_editor.read_write ) {
    this.focused_editor.focus();
    if ( this.toggle_image_button( "createLink" ) )
      this.focused_editor.start_link();
    else
      link = this.focused_editor.end_link();

    this.display_link_pulldown( this.focused_editor, link );
  }

  event.stop();
}

Wiki.prototype.hide_editor = function ( event, editor ) {
  this.clear_messages();
  this.clear_pulldowns();

  if ( editor == this.focused_editor )
    this.focused_editor = null;

  if ( !editor ) {
    editor = this.focused_editor;
    this.focused_editor = null;
  }

  if ( editor ) {
    // if the editor to hide is completely empty, then simply remove it
    if ( editor.id == this.blank_editor_id && editor.empty() ) {
      this.remove_all_notes_link( editor.id );
      editor.shutdown();
      this.decrement_total_notes_count();
    } else {
      // before hiding an editor, save it
      if ( this.notebook.read_write && editor.read_write )
        this.save_editor( editor );

      editor.shutdown();
      Highlight( "all_notes_link" );
    }

    this.display_empty_message();
  }

  event.stop();
}

Wiki.prototype.delete_editor = function ( event, editor ) {
  this.clear_messages();
  this.clear_pulldowns();

  if ( !editor ) {
    editor = this.focused_editor;
    this.focused_editor = null;
  }

  if ( editor ) {
    if ( this.startup_notes[ editor.id ] )
      delete this.startup_notes[ editor.id ];

    this.save_editor( editor, true );

    var self = this;
    if ( this.notebook.read_write && editor.read_write ) {
      this.invoker.invoke( "/notebooks/delete_note", "POST", { 
        "notebook_id": this.notebook_id,
        "note_id": editor.id
      }, function ( result ) { self.display_storage_usage( result.storage_bytes ); } );
    }

    if ( editor == this.focused_editor )
      this.focused_editor = null;

    if ( this.notebook.trash_id && !( editor.id == this.blank_editor_id && editor.empty() ) ) {
      var undo_button = createDOM( "input", {
        "type": "button",
        "class": "message_button",
        "value": "undo",
        "title": "undo deletion"
      } );
      var trash_link = createDOM( "a", {
        "href": "/notebooks/" + this.notebook.trash_id + "?parent_id=" + this.notebook.object_id
      }, "trash" );
      var message_div = this.display_message( "The note has been moved to the", [ trash_link, ". ", undo_button ], editor.iframe );
      var self = this;
      connect( undo_button, "onclick", function ( event ) { self.undelete_editor_via_undo( event, editor, message_div ); } );
    }

    this.remove_all_notes_link( editor.id );

    editor.shutdown();
    this.decrement_total_notes_count();
    this.display_empty_message();
  }

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

    this.save_editor( editor, true );

    if ( this.notebook.read_write && editor.read_write ) {
      var self = this;
      this.invoker.invoke( "/notebooks/undelete_note", "POST", { 
        "notebook_id": editor.deleted_from_id,
        "note_id": editor.id
      }, function ( result ) { self.display_storage_usage( result.storage_bytes ); } );
    }

    if ( editor == this.focused_editor )
      this.focused_editor = null;

    this.remove_all_notes_link( editor.id );

    editor.shutdown();
    this.decrement_total_notes_count();
    this.display_empty_message();
  }

  event.stop();
}

Wiki.prototype.undelete_editor_via_undo = function( event, editor, position_after ) {
  if ( editor ) {
    if ( this.notebook.read_write && editor.read_write ) {
      var self = this;
      this.invoker.invoke( "/notebooks/undelete_note", "POST", { 
        "notebook_id": this.notebook_id,
        "note_id": editor.id
      }, function ( result ) { self.display_storage_usage( result.storage_bytes ); } );
    }

    this.startup_notes[ editor.id ] = true;
    this.increment_total_notes_count();
    this.load_editor( "Note not found.", editor.id, null, null, position_after );
  }

  event.stop();
}

Wiki.prototype.undelete_editor_via_undelete = function( event, note_id, position_after ) {
  if ( this.notebook.read_write ) {
    var self = this;
    this.invoker.invoke( "/notebooks/undelete_note", "POST", { 
      "notebook_id": this.notebook_id,
      "note_id": note_id
    }, function ( result ) { self.display_storage_usage( result.storage_bytes ); } );
  }

  this.startup_notes[ note_id ] = true;
  this.increment_total_notes_count();
  this.load_editor( "Note not found.", note_id, null, null, position_after );

  event.stop();
}


Wiki.prototype.compare_versions = function( event, editor, previous_revision ) {
  this.clear_pulldowns();

  // display the two revisions for comparison by the user
  this.load_editor( editor.title, editor.id, previous_revision, null, editor.iframe );
  this.load_editor( editor.title, editor.id, null, null, editor.iframe );
}

Wiki.prototype.save_editor = function ( editor, fire_and_forget ) {
  if ( !editor )
    editor = this.focused_editor;

  var self = this;
  if ( editor && editor.read_write && !( editor.id == this.blank_editor_id && editor.empty() ) ) {
    this.invoker.invoke( "/notebooks/save_note", "POST", { 
      "notebook_id": this.notebook_id,
      "note_id": editor.id,
      "contents": editor.contents(),
      "startup": editor.startup,
      "previous_revision": editor.revision ? editor.revision : "None"
    }, function ( result ) {
      self.update_editor_revisions( result, editor );
      self.display_storage_usage( result.storage_bytes );
    }, null, fire_and_forget );
  }
}

Wiki.prototype.update_editor_revisions = function ( result, editor ) {
  // if there's not a newly saved revision, then the contents are unchanged, so bail
  if ( !result.new_revision )
    return;

  var client_previous_revision = editor.revision;
  editor.revision = result.new_revision;

  // if the server's idea of the previous revision doesn't match the client's, then someone has
  // gone behind our back and saved the editor's note from another window
  if ( result.previous_revision != client_previous_revision ) {
    var compare_button = createDOM( "input", {
      "type": "button",
      "class": "message_button",
      "value": "compare versions",
      "title": "compare your version with the modified version"
    } );
    this.display_error( 'Your changes to the note titled "' + editor.title + '" have overwritten changes made in another window.', [ compare_button ], editor.iframe );

    var self = this;
    connect( compare_button, "onclick", function ( event ) {
      self.compare_versions( event, editor, result.previous_revision );
    } );

    if ( !editor.revisions_list || editor.revisions_list.length == 0 )
      return;
    editor.revisions_list.push( result.previous_revision );
  }

  // add the new revision to the editor's revisions list
  if ( !editor.revisions_list || editor.revisions_list.length == 0 )
    return;
  editor.revisions_list.push( result.new_revision );
}

Wiki.prototype.search = function ( event ) {
  this.clear_messages();
  this.clear_pulldowns();

  var self = this;
  this.invoker.invoke( "/notebooks/search", "GET", {
      "notebook_id": this.notebook_id
    },
    function( result ) { self.display_search_results( result ); },
    "search_form"
  );

  event.stop();
}

Wiki.prototype.display_search_results = function ( result ) {
  // if there are no search results, indicate that and bail
  if ( !result || result.notes.length == 0 ) {
    this.display_message( "No matching notes.", undefined, getElement( "notes_top" ) );
    return;
  }

  // otherwise, there are multiple search results, so create a "magic" search results note. but
  // first close any open search results notes
  if ( this.search_results_editor )
    this.search_results_editor.shutdown();

  var list = createDOM( "span", {} );
  for ( var i in result.notes ) {
    var note = result.notes[ i ]
    if ( !note.title ) continue;

    if ( note.contents.length == 0 ) {
      var preview = "empty note";
    } else {
      var preview = note.contents;

      // if the preview appears not to end with a complete sentence, add "..."
      if ( !/[?!.]\s*$/.test( preview ) )
        preview = preview + " <b>...</b>";
    }

    var preview_span = createDOM( "span" );
    preview_span.innerHTML = preview;

    appendChildNodes( list,
      createDOM( "p", {},
        createDOM( "a", { "href": "/notebooks/" + this.notebook_id + "?note_id=" + note.object_id }, note.title ),
        createDOM( "br" ),
        preview_span
      )
    );
  }

  this.search_results_editor = this.create_editor( "search_results", "<h3>search results</h3>" + list.innerHTML, undefined, undefined, undefined, false, true, true, getElement( "notes_top" ) );
}

Wiki.prototype.display_all_notes_list = function ( result ) {
  this.clear_messages();
  this.clear_pulldowns();

  if ( this.display_empty_message() == true )
    return;

  if ( this.all_notes_editor )
    this.all_notes_editor.shutdown();

  // build up a list of all notes in this notebook, one link per note
  var list = createDOM( "ul", { "id": "notes_list" } );
  if ( this.focused_editor )
    appendChildNodes( list, this.create_all_notes_link( this.focused_editor.id, this.focused_editor.title || "untitled note" ) );

  for ( var i in result.notes ) {
    var note_tuple = result.notes[ i ]
    var note_id = note_tuple[ 0 ];
    var note_title = note_tuple[ 1 ];
    if ( this.focused_editor && note_id == this.focused_editor.id )
      continue;
    if ( !note_title )
      note_title = "untitled note";

    appendChildNodes( list, this.create_all_notes_link( note_id, note_title ) );
  }
  var list_holder = createDOM( "div", {}, list );

  this.all_notes_editor = this.create_editor( "all_notes", "<h3>all notes</h3>" + list_holder.innerHTML, undefined, undefined, undefined, false, true, true, getElement( "notes_top" ) );
}

Wiki.prototype.display_message = function ( text, nodes, position_after ) {
  this.clear_messages();
  this.clear_pulldowns();

  var inner_div = DIV( { "class": "message_inner" }, text + " " );
  for ( var i in nodes )
    appendChildNodes( inner_div, nodes[ i ] );

  ok_button = createDOM( "input", {
    "type": "button",
    "class": "message_button",
    "value": "ok",
    "title": "dismiss this message"
  } );
  appendChildNodes( inner_div, ok_button );
  connect( ok_button, "onclick", this.clear_messages );

  var div = DIV( { "class": "message" }, inner_div );
  div.nodes = nodes;

  if ( position_after )
    insertSiblingNodesAfter( position_after, div )
  else if ( this.focused_editor )
    insertSiblingNodesAfter( this.focused_editor.iframe, div )
  else
    appendChildNodes( "notes", div );

  return div;
}

Wiki.prototype.display_error = function ( text, nodes, position_after ) {
  this.clear_messages();
  this.clear_pulldowns();

  // remove all empty editors, some of which might exist due to a problem reaching the server
  var iframes = getElementsByTagAndClassName( "iframe", "note_frame" );
  for ( var i in iframes ) {
    var editor = iframes[ i ].editor;
    if ( editor.empty() )
      editor.shutdown();
  }

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
  connect( ok_button, "onclick", this.clear_messages );

  var div = DIV( { "class": "error" }, inner_div );
  div.nodes = nodes;

  if ( position_after )
    insertSiblingNodesAfter( position_after, div )
  else if ( this.focused_editor )
    insertSiblingNodesAfter( this.focused_editor.iframe, div )
  else
    appendChildNodes( "notes", div );

  return div;
}

Wiki.prototype.clear_messages = function () {
  var results = getElementsByTagAndClassName( "div", "message" );

  for ( var i in results ) {
    var result = results[ i ];
    blindUp( result, options = { "duration": 0.5, afterFinish: function () {
      try {
        for ( var j in result.nodes )
          disconnectAll( result.nodes[ j ] );
        removeElement( result );
      } catch ( e ) { }
    } } );
  }

  var results = getElementsByTagAndClassName( "div", "error" );

  for ( var i in results ) {
    var result = results[ i ];
    blindUp( result, options = { "duration": 0.5, afterFinish: function () {
      try {
        removeElement( result );
      } catch ( e ) { }
    } } );
  }
}

Wiki.prototype.clear_pulldowns = function () {
  var results = getElementsByTagAndClassName( "div", "pulldown" );

  for ( var i in results ) {
    var result = results[ i ];

    // close the pulldown if it's been open at least a quarter second
    if ( new Date() - result.pulldown.init_time >= 250 )
      result.pulldown.shutdown();
  }
}

Wiki.prototype.delete_all_editors = function ( event ) {
  this.clear_messages();
  this.clear_pulldowns();

  this.startup_notes = new Array();

  if ( this.notebook.read_write ) {
    var self = this;
    this.invoker.invoke( "/notebooks/delete_all_notes", "POST", { 
      "notebook_id": this.notebook_id
    }, function ( result ) { self.display_storage_usage( result.storage_bytes ); } );
  }

  this.focused_editor = null;

  var iframes = getElementsByTagAndClassName( "iframe", "note_frame" );
  for ( var i in iframes ) {
    var editor = iframes[ i ].editor;
    editor.shutdown();
  }

  this.zero_total_notes_count();
  this.display_empty_message();

  event.stop();
}

Wiki.prototype.display_empty_message = function () {
  var iframes = getElementsByTagAndClassName( "iframe", "note_frame" );

  // if there are any messages already open, bail
  var messages = getElementsByTagAndClassName( "div", "message" );
  if ( messages.length > 0 ) return false;

  // if there are any errors open, bail
  var errors = getElementsByTagAndClassName( "div", "error" );
  if ( errors.length > 0 ) return false;

  // if there are any open editors, bail
  for ( var i in iframes ) {
    var iframe = iframes[ i ];
    if ( iframe.editor.closed == false )
      return false;
  }  

  if ( !this.total_notes_count ) {
    if ( this.parent_id )
      this.display_message( "The trash is empty." )
    else
      this.display_message( "This notebook is empty." );
    return true;
  }

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
}

Wiki.prototype.decrement_total_notes_count = function () {
  if ( this.total_notes_count == null ) return;
  this.total_notes_count -= 1;
  replaceChildNodes( "total_notes_count", this.total_notes_count );
}

Wiki.prototype.zero_total_notes_count = function () {
  if ( this.total_notes_count == null ) return;
  this.total_notes_count = 0;
  replaceChildNodes( "total_notes_count", this.total_notes_count );
}

Wiki.prototype.remove_all_notes_link = function ( note_id ) {
  if ( !this.all_notes_editor ) return;

  withDocument( this.all_notes_editor.document, function () {
    var note_link = getElement( "note_link_" + note_id );
    if ( note_link )
      removeElement( note_link );
  } );

  this.all_notes_editor.resize();
}

Wiki.prototype.add_all_notes_link = function ( note_id, note_title ) {
  if ( !this.all_notes_editor ) return;
  if ( note_title == "all notes" || note_title == "search results" ) return;

  if ( !note_title || note_title.length == 0 )
    note_title = "untitled note";

  var self = this;
  withDocument( this.all_notes_editor.document, function () {
    // if the note link already exists, update its title and bail
    var note_link = getElement( "note_link_" + note_id );
    if ( note_link ) {
      replaceChildNodes( note_link.firstChild, note_title );
      self.all_notes_editor.resize();
      return;
    }

    var notes_list = getElement( "notes_list" );
    if ( !notes_list ) return;
    var first_note_link = notes_list.firstChild;
    var new_note_link = self.create_all_notes_link( note_id, note_title );

    if ( first_note_link )
      insertSiblingNodesBefore( first_note_link, new_note_link );
    else
      appendChildNodes( notes_list, new_note_link );
  } );

  this.all_notes_editor.resize();
}

Wiki.prototype.create_all_notes_link = function ( note_id, note_title ) {
  return createDOM( "li", { "id": "note_link_" + note_id },
    createDOM( "a", { "href": "/notebooks/" + this.notebook_id + "?note_id=" + note_id }, note_title )
  );
}

Wiki.prototype.start_notebook_rename = function () {
  this.clear_messages();
  this.clear_pulldowns();

  // if a renaming is already in progress, end the renaming instead of starting one
  var notebook_name_field = getElement( "notebook_name_field" );
  if ( notebook_name_field ) {
    this.end_notebook_rename();
    return; 
  }

  notebook_name_field = createDOM(
    "input", {
      "type": "text",
      "value": this.notebook.name,
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
      "value": "ok",
      "title": "dismiss this message"
    }
  );

  var rename_form = createDOM(
    "form", { "id": "rename_form" }, notebook_name_field, ok_button
  );

  replaceChildNodes( "notebook_header_area", rename_form );

  var self = this;
  connect( rename_form, "onsubmit", function ( event ) {
    self.end_notebook_rename();
    event.stop();
  } );
  connect( ok_button, "onclick", function ( event ) {
    self.end_notebook_rename();
    event.stop();
  } );

  notebook_name_field.focus();
  notebook_name_field.select();
}

Wiki.prototype.end_notebook_rename = function () {
  var new_notebook_name = getElement( "notebook_name_field" ).value;

  // if the new name is blank or reserved, don't actually rename the notebook
  if ( /^\s*$/.test( new_notebook_name ) )
    new_notebook_name = this.notebook.name;

  if ( /^\s*Luminotes/.test( new_notebook_name ) || /^\s*trash\s*$/.test( new_notebook_name ) ) {
    new_notebook_name = this.notebook.name;
    this.display_error( "That notebook name is not available. Please try a different one." );
  }

  // rename the notebook in the header
  var notebook_header_name = createDOM(
    "span",
    { "id": "notebook_header_name" },
    createDOM( "strong", {}, new_notebook_name )
  );
  replaceChildNodes( "notebook_header_area", notebook_header_name );

  var self = this;
  connect( notebook_header_name, "onclick", function ( event ) {
    self.start_notebook_rename();
    event.stop();
  } );

  // rename the notebook link on the right side of the page
  replaceChildNodes(
    "notebook_" + this.notebook.object_id,
    document.createTextNode( new_notebook_name )
  );

  // if the name has changed, then send the new name to the server
  if ( new_notebook_name == this.notebook.name )
    return;

  this.notebook.name = new_notebook_name;
  this.invoker.invoke( "/notebooks/rename", "POST", {
    "notebook_id": this.notebook_id,
    "name": new_notebook_name
  } );
}

Wiki.prototype.toggle_editor_changes = function ( event, editor ) {
  // if the pulldown is already open, then just close it
  var pulldown_id = "changes_" + editor.id;
  var existing_div = getElement( pulldown_id );
  if ( existing_div ) {
    existing_div.pulldown.shutdown();
    return;
  }

  event.stop();

  // if there's already a cached revision list, or the editor doesn't have a revision yet, then
  // display the changes pulldown and bail
  if ( ( editor.revisions_list && editor.revisions_list.length > 0 ) || !editor.revision ) {
    new Changes_pulldown( this, this.notebook_id, this.invoker, editor );
    return;
  }

  // otherwise, load the revision list for this note from the server
  var self = this;
  this.invoker.invoke(
    "/notebooks/load_note_revisions", "GET", {
      "notebook_id": this.notebook_id,
      "note_id": editor.id
    },
    function ( result ) {
      editor.revisions_list = result.revisions;
      new Changes_pulldown( self, self.notebook_id, self.invoker, editor );
    }
  );
}

Wiki.prototype.toggle_editor_options = function ( event, editor ) {
  // if the pulldown is already open, then just close it
  var pulldown_id = "options_" + editor.id;
  var existing_div = getElement( pulldown_id );
  if ( existing_div ) {
    existing_div.pulldown.shutdown();
    return;
  }

  new Options_pulldown( this, this.notebook_id, this.invoker, editor );
  event.stop();
}

connect( window, "onload", function ( event ) { new Wiki( new Invoker() ); } );


function Pulldown( wiki, notebook_id, pulldown_id, anchor, relative_to ) {
  this.wiki = wiki;
  this.notebook_id = notebook_id;
  this.div = createDOM( "div", { "id": pulldown_id, "class": "pulldown" } );
  this.div.pulldown = this;
  this.init_time = new Date();
  this.anchor = anchor;
  this.relative_to = relative_to;

  addElementClass( this.div, "invisible" );

  appendChildNodes( document.body, this.div );
  var position = calculate_position( anchor, relative_to );
  setElementPosition( this.div, position );

  removeElementClass( this.div, "invisible" );
}

function calculate_position( anchor, relative_to ) {
  // position the pulldown under the anchor
  var position = getElementPosition( anchor );

  if ( relative_to ) {
    var relative_pos = getElementPosition( relative_to );
    if ( relative_pos ) {
      position.x += relative_pos.x;
      position.y += relative_pos.y;

      // Work around an IE "feature" in which an element within an iframe changes its absolute
      // position based on how far the page is scrolled. The if is necessary to prevent this
      // workaround from screwing positions up in sane browsers like Firefox.
      if ( getStyle( "content", "position" ) == "absolute" )
        position.y -= getElement( "html" ).scrollTop;

    }
  }

  var anchor_dimensions = getElementDimensions( anchor );

  // if the anchor has no height, move the position down a bit by an arbitrary amount
  if ( anchor_dimensions.h == 0 )
    position.y += 8;
  else
    position.y += anchor_dimensions.h + 4;

  return position;
}

Pulldown.prototype.update_position = function () {
  var position = calculate_position( this.anchor, this.relative_to );
  setElementPosition( this.div, position );
}

Pulldown.prototype.shutdown = function () {
  removeElement( this.div );
}


function Options_pulldown( wiki, notebook_id, invoker, editor ) {
  Pulldown.call( this, wiki, notebook_id, "options_" + editor.id, editor.options_button );

  this.invoker = invoker;
  this.editor = editor;
  this.startup_checkbox = createDOM( "input", { "type": "checkbox", "class": "pulldown_checkbox" } );
  this.startup_toggle = createDOM( "a", { "href": "", "class": "pulldown_link", "title": "Display this note whenever the notebook is loaded." },
    "show on startup"
  );

  appendChildNodes( this.div, this.startup_checkbox );
  appendChildNodes( this.div, this.startup_toggle );
  this.startup_checkbox.checked = editor.startup;

  var self = this;
  connect( this.startup_checkbox, "onclick", function ( event ) { self.startup_clicked( event ); } );
  connect( this.startup_toggle, "onclick", function ( event ) { self.startup_clicked( event ); event.stop(); } );
}

Options_pulldown.prototype = new function () { this.prototype = Pulldown.prototype; };
Options_pulldown.prototype.constructor = Options_pulldown;

Options_pulldown.prototype.startup_clicked = function ( event ) {
  if ( event.target() != this.startup_checkbox )
    this.startup_checkbox.checked = this.startup_checkbox.checked ? false : true;
  this.editor.startup = this.startup_checkbox.checked;

  // save this note along with its toggled startup state
  this.wiki.save_editor( this.editor );
}

Options_pulldown.prototype.shutdown = function () {
  Pulldown.prototype.shutdown.call( this );

  disconnectAll( this.startup_checkbox );
  disconnectAll( this.startup_toggle );
}


function Changes_pulldown( wiki, notebook_id, invoker, editor ) {
  Pulldown.call( this, wiki, notebook_id, "changes_" + editor.id, editor.changes_button );

  this.invoker = invoker;
  this.editor = editor;
  this.links = new Array();
  
  if ( !editor.revisions_list || editor.revisions_list.length == 0 ) {
    appendChildNodes( this.div, createDOM( "span", "This note has no previous changes." ) );
    return;
  }

  // display list of revision timestamps in reverse chronological order
  var revisions_list = clone( editor.revisions_list );
  revisions_list.reverse();

  var self = this;
  for ( var i = 0; i < revisions_list.length - 1; ++i ) { // -1 to skip the oldest revision
    var revision = revisions_list[ i ];
    var short_revision = this.wiki.brief_revision( revision );
    var href = "/notebooks/" + this.notebook_id + "?" + queryString(
      [ "note_id", "revision" ],
      [ this.editor.id, revision ]
    );
    var link = createDOM( "a", { "href": href, "class": "pulldown_link" }, short_revision );
    this.links.push( link );
    link.revision = revision;
    connect( link, "onclick", function ( event ) { self.link_clicked( event, self.editor.id ); } );
    appendChildNodes( this.div, link );
    appendChildNodes( this.div, createDOM( "br" ) );
  }
}

Changes_pulldown.prototype = new function () { this.prototype = Pulldown.prototype; };
Changes_pulldown.prototype.constructor = Changes_pulldown;

Changes_pulldown.prototype.link_clicked = function( event, note_id ) {
  var revision = event.target().revision;
  this.wiki.load_editor( "Revision not found.", note_id, revision, null, this.editor.iframe );
  event.stop();
}

Changes_pulldown.prototype.shutdown = function () {
  Pulldown.prototype.shutdown.call( this );

  for ( var i in this.links )
    disconnectAll( this.links[ i ] );
}


function Link_pulldown( wiki, notebook_id, invoker, editor, link ) {
  link.pulldown = this;
  this.link = link;

  Pulldown.call( this, wiki, notebook_id, "link_" + editor.id, link, editor.iframe );

  this.invoker = invoker;
  this.editor = editor;
  this.title_field = createDOM( "input", { "class": "text_field", "size": "30", "maxlength": "256" } );
  this.note_preview = createDOM( "span", {} );
  this.previous_title = "";

  var self = this;
  connect( this.title_field, "onclick", function ( event ) { self.title_field_clicked( event ); } );
  connect( this.title_field, "onfocus", function ( event ) { self.title_field_focused( event ); } );
  connect( this.title_field, "onchange", function ( event ) { self.title_field_changed( event ); } );
  connect( this.title_field, "onblur", function ( event ) { self.title_field_changed( event ); } );
  connect( this.title_field, "onkeydown", function ( event ) { self.title_field_key_pressed( event ); } );

  appendChildNodes( this.div, createDOM( "span", { "class": "field_label" }, "links to: " ) );
  appendChildNodes( this.div, this.title_field );
  appendChildNodes( this.div, this.note_preview );

  // links with targets are considered links to external sites
  if ( link.target ) {
    this.title_field.value = link.href;
    replaceChildNodes( this.note_preview, "web link" );
    return;
  }

  var query = parse_query( link );
  var title = link_title( link, query );
  var id = query.note_id;

  // if the note has no destination note id set, try loading the note from the server by title
  if ( ( id == undefined || id == "new" || id == "null" ) && title.length > 0 ) {
    if ( title == "all notes" ) {
      this.title_field.value = title;
      this.display_preview( title, "list of all notes in this notebook" );
      return;
    }

    if ( title == "search results" ) {
      this.title_field.value = title;
      this.display_preview( title, "current search results" );
      return;
    }

    this.invoker.invoke(
      "/notebooks/load_note_by_title", "GET", {
        "notebook_id": this.notebook_id,
        "note_title": title
      },
      function ( result ) {
        // if the user has already started typing something, don't overwrite it
        if ( self.title_field.value.length != 0 )
          return;
        if ( result.note ) {
          self.title_field.value = result.note.title;
          self.display_preview( result.note.title, result.note.contents );
        } else {
          self.title_field.value = title;
          replaceChildNodes( self.note_preview, "empty note" );
        }
      }
    );
    return;
  }

  // if this link has an actual destination note id set, then see if that note is already open. if
  // so, display its title and a preview of its contents
  var iframe = getElement( "note_" + id );
  if ( iframe ) {
    this.title_field.value = iframe.editor.title;
    this.display_preview( iframe.editor.title, iframe.editor.document );
    return;
  }

  // otherwise, load the destination note from the server, displaying its title and a preview of
  // its contents
  this.invoker.invoke(
    "/notebooks/load_note", "GET", {
      "notebook_id": this.notebook_id,
      "note_id": id
    },
    function ( result ) {
      // if the user has already started typing something, don't overwrite it
      if ( self.title_field.value.length != 0 )
        return;
      if ( result.note ) {
        self.title_field.value = result.note.title;
        self.display_preview( result.note.title, result.note.contents );
      } else {
        self.title_field.value = title;
        replaceChildNodes( self.note_preview, "empty note" );
      }
    }
  );
}

Link_pulldown.prototype = new function () { this.prototype = Pulldown.prototype; };
Link_pulldown.prototype.constructor = Link_pulldown;

Link_pulldown.prototype.display_preview = function ( title, contents ) {
  if ( !contents ) {
    replaceChildNodes( this.note_preview, "empty note" );
    return;
  }

  // if contents is a DOM node, just scrape its text
  if ( contents.nodeType ) {
    contents = strip( scrapeText( contents ) );
  // otherwise, assume contents is a string, so put it into a DOM node and then scrape its contents
  } else {
    var contents_node = createDOM( "span", {} );
    contents_node.innerHTML = contents;
    contents = strip( scrapeText( contents_node ) );
  }

  // remove the title from the scraped contents text
  if ( contents.indexOf( title ) == 0 )
    contents = contents.substr( title.length );

  if ( contents.length == 0 ) {
    replaceChildNodes( this.note_preview, "empty note" );
  } else {
    var max_preview_length = 40;
    var preview = contents.substr( 0, max_preview_length ) + ( ( contents.length > max_preview_length ) ? "..." : "" );
    replaceChildNodes( this.note_preview, preview );
  }
}

Link_pulldown.prototype.title_field_clicked = function ( event ) {
  event.stop();
}

Link_pulldown.prototype.title_field_focused = function ( event ) {
  this.title_field.select();
}

Link_pulldown.prototype.title_field_changed = function ( event ) {
  // if the title is actually unchanged, then bail
  if ( this.title_field.value == this.previous_title )
    return;

  replaceChildNodes( this.note_preview, "" );
  var title = strip( this.title_field.value );
  this.previous_title = title;

  var self = this;
  this.wiki.resolve_link( title, this.link, function ( contents ) {
    self.display_preview( title, contents );
  } );
}

Link_pulldown.prototype.title_field_key_pressed = function ( event ) {
  // if enter is pressed, consider the title field altered. this is necessary because IE neglects
  // to issue an onchange event when enter is pressed in an input field
  if ( event.key().code == 13 ) {
    this.title_field_changed();
    event.stop();
  }
}

Link_pulldown.prototype.update_position = function ( anchor, relative_to ) {
  Pulldown.prototype.update_position.call( this, anchor, relative_to );
}

Link_pulldown.prototype.shutdown = function () {
  Pulldown.prototype.shutdown.call( this );

  disconnectAll( this.title_field );
  if ( this.link )
    this.link.pulldown = null;
}
