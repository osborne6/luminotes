function Wiki() {
  this.next_id = null;
  this.focused_editor = null;
  this.blank_editor_id = null;
  this.notebook = null;
  this.notebook_id = getElement( "notebook_id" ).value;
  this.parent_id = getElement( "parent_id" ).value; // id of the notebook containing this one
  this.read_write = false;
  this.startup_notes = new Array();  // map of startup notes: note id to bool
  this.open_editors = new Array();   // map of open notes: note title to editor
  this.invoker = new Invoker();
  this.search_titles_only = true;

  connect( this.invoker, "error_message", this, "display_error" );
  connect( "search_form", "onsubmit", this, "search" );
  connect( "search_button", "onclick", this, "toggle_search_options" );

  // get info on the requested notebook (if any)
  var self = this;
  if ( this.notebook_id ) {
    this.invoker.invoke(
      "/notebooks/contents", "GET", {
        "notebook_id": this.notebook_id,
        "note_id": getElement( "note_id" ).value,
        "revision": getElement( "revision" ).value
      },
      function( result ) { self.populate( result ); }
    );
    var include_startup_notes = false;
  } else {
    var include_startup_notes = true;
  }

  // get info on the current user (logged-in or anonymous)
  this.invoker.invoke( "/users/current", "GET", {
      "include_startup_notes": include_startup_notes
    },
    function( result ) { self.display_user( result ); }
  );
}

Wiki.prototype.update_next_id = function ( result ) {
  this.next_id = result.next_id;
}

Wiki.prototype.display_user = function ( result ) {
  // if no notebook id was requested, then just display the user's default notebook
  if ( !this.notebook_id ) {
    this.notebook_id = result.notebooks[ 0 ].object_id;
    this.populate( { "notebook" : result.notebooks[ 0 ], "startup_notes": result.startup_notes } );
  }

  if ( result.user.username == "anonymous" )
    return;

  // display links for current notebook and a list of all notebooks that the user has access to
  var span = createDOM( "span" );
  replaceChildNodes( "notebooks_area", span );

  appendChildNodes( span, createDOM( "h3", "notebooks" ) );

  for ( var i in result.notebooks ) {
    var notebook = result.notebooks[ i ];

    if ( notebook.name == "Luminotes" )
      continue;

    var div_class = "link_area_item";
    if ( notebook.object_id == this.notebook_id )
      div_class += " current_notebook_name";

    appendChildNodes( span, createDOM( "div", {
      "class": div_class
    }, createDOM( "a", {
      "href": "/notebooks/" + notebook.object_id,
      "id": "notebook_" + notebook.object_id
    }, notebook.name ) ) );
  }

  // display the name of the logged in user and a logout link
  span = createDOM( "span" );
  replaceChildNodes( "user_area", span );
  appendChildNodes( span, "logged in as " + result.user.username );
  appendChildNodes( span, " | " );
  appendChildNodes( span, createDOM( "a", { "href": result.http_url + "/", "id": "logout_link" }, "logout" ) );

  var self = this;
  connect( "logout_link", "onclick", function ( event ) {
    self.save_editor( null, true );
    self.invoker.invoke( "/users/logout", "POST" );
    event.stop();
  } );
}

Wiki.prototype.populate = function ( result ) {
  this.notebook = result.notebook;
  var self = this;

  var header_area = getElement( "notebook_header_area" );
  replaceChildNodes( header_area, createDOM( "b", {}, this.notebook.name ) );
  if ( this.parent_id ) {
    appendChildNodes( header_area, createDOM( "span", {}, " | " ) );
    appendChildNodes( header_area, createDOM( "a", { "href": "/notebooks/" + this.parent_id }, "return to notebook" ) );
  }

  var span = createDOM( "span" );
  replaceChildNodes( "this_notebook_area", span );

  appendChildNodes( span, createDOM( "h3", "this notebook" ) );
  appendChildNodes( span, createDOM( "div", { "class": "link_area_item" },
    createDOM( "a", { "href": "/notebooks/" + this.notebook.object_id, "id": "recent_notes_link", "title": "View the most recently updated notes." }, "recent notes" )
  ) );
  appendChildNodes( span, createDOM( "div", { "class": "link_area_item" },
    createDOM( "a", { "href": "/notebooks/download_html/" + this.notebook.object_id, "id": "download_html_link", "title": "Download a stand-alone copy of the entire wiki notebook." }, "download as html" )
  ) );

  if ( this.notebook.read_write ) {
    this.read_write = true;
    removeElementClass( "toolbar", "undisplayed" );

    if ( this.notebook.trash ) {
      appendChildNodes( span, createDOM( "div", { "class": "link_area_item" },
        createDOM( "a", {
          "href": "/notebooks/" + this.notebook.trash.object_id + "?parent_id=" + this.notebook.object_id,
          "id": "trash_link",
          "title": "Look here for notes you've deleted."
        }, "trash" )
      ) );
    } else if ( this.notebook.name == "trash" ) {
      appendChildNodes( span, createDOM( "div", { "class": "link_area_item current_trash_notebook_name" },
        createDOM( "a", {
          "href": location.href,
          "id": "trash_link",
          "title": "Look here for notes you've deleted."
        }, "trash" )
      ) );

      var header_area = getElement( "notebook_header_area" )
      removeElementClass( header_area, "current_notebook_name" );
      addElementClass( header_area, "current_trash_notebook_name" );

      var border = getElement( "notebook_border" )
      removeElementClass( border, "current_notebook_name" );
      addElementClass( border, "current_trash_notebook_name" );
    }

    connect( window, "onunload", function ( event ) { self.editor_focused( null, true ); } );
    connect( "bold", "onclick", function ( event ) { self.toggle_button( event, "bold" ); } );
    connect( "italic", "onclick", function ( event ) { self.toggle_button( event, "italic" ); } );
    connect( "underline", "onclick", function ( event ) { self.toggle_button( event, "underline" ); } );
    connect( "title", "onclick", function ( event ) { self.toggle_button( event, "title", "h3" ); } );
    connect( "insertUnorderedList", "onclick", function ( event ) { self.toggle_button( event, "insertUnorderedList" ); } );
    connect( "insertOrderedList", "onclick", function ( event ) { self.toggle_button( event, "insertOrderedList" ); } );
    connect( "createLink", "onclick", this, "toggle_link_button" );
    connect( "newNote", "onclick", this, "create_blank_editor" );

    // grab the next available object id
    this.invoker.invoke( "/next_id", "POST", null,
      function( result ) { self.update_next_id( result ); }
    );
  }

  var self = this;
  connect( "recent_notes_link", "onclick", function ( event ) {
    self.invoker.invoke(
      "/notebooks/recent_notes", "GET", { "notebook_id": self.notebook.object_id },
      function( result ) { self.display_loaded_notes( result ); }
    );
    event.stop();
  } );

  connect( "download_html_link", "onclick", function ( event ) {
    self.save_editor( null, true );
  } );

  // create an editor for each startup note in the received notebook, focusing the first one
  var focus = true;
  for ( var i in result.startup_notes ) {
    var note = result.startup_notes[ i ];
    if ( !note ) continue;
    this.startup_notes[ note.object_id ] = true;

    // don't actually create an editor if a particular note was provided in the result
    if ( !result.note ) {
      this.create_editor( note.object_id, note.contents, note.deleted_from, note.revisions_list, undefined, this.read_write, false, focus );
      focus = false;
    }
  }

  // if one particular note was provided, then just display an editor for that note
  var read_write = this.read_write;
  if ( getElement( "revision" ).value ) read_write = false;
  if ( result.note )
    this.create_editor( result.note.object_id, result.note.contents, result.note.deleted_from, result.note.revisions_list, undefined, read_write, false, true );

  if ( !this.notebook.trash && result.startup_notes.length == 0 && !result.note )
    this.display_message( "There are no notes here." )
}

Wiki.prototype.create_blank_editor = function ( event ) {
  if ( event ) event.stop();

  // if there is already a blank editor, then highlight it and bail
  if ( this.blank_editor_id != null ) {
    var blank_iframe_id = "note_" + this.blank_editor_id;
    var iframe = getElement( blank_iframe_id );
    if ( iframe && iframe.editor.empty() ) {
      iframe.editor.highlight();
      return;
    }
  }

  this.blank_editor_id = this.create_editor( undefined, undefined, undefined, undefined, undefined, this.read_write, true, true );
}

Wiki.prototype.load_editor = function ( note_title, note_id, revision, link ) {
  // if a link is given with an open link pulldown, then ignore the note title given and use the
  // one from the pulldown instead
  if ( link ) {
    var pulldown = link.pulldown;
    var pulldown_title = undefined;
    if ( pulldown ) {
      pulldown_title = strip( pulldown.title_field.value );
      if ( pulldown_title )
        note_title = pulldown_title;
      else
        pulldown.title_field.value = note_title;
    }

    // if the title looks like a URL, then make it a link to an external site
    if ( /^\w+:\/\//.test( note_title ) ) {
      link.target = "_new";
      link.href = note_title;
      window.open( link.href );
      return
    }
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

  // if the note corresponding to the link's title is already open, highlight it and bail
  if ( !revision ) {
    var editor = this.open_editors[ note_title ];
    if ( editor ) {
      editor.highlight();
      if ( link )
        link.href = "/notebooks/" + this.notebook_id + "?note_id=" + editor.id;
      return;
    }
  }

  // if there's not a valid destination note id, then load by title instead of by id
  var self = this;
  if ( note_id == undefined || note_id == "new" || note_id == "null" ) {
    this.invoker.invoke(
      "/notebooks/load_note_by_title", "GET", {
        "notebook_id": this.notebook_id,
        "note_title": note_title,
        "revision": revision
      },
      function ( result ) { self.parse_loaded_editor( result, note_title, revision, link ); }
    );
    return;
  }

  this.invoker.invoke(
    "/notebooks/load_note", "GET", {
      "notebook_id": this.notebook_id,
      "note_id": note_id,
      "revision": revision
    },
    function ( result ) { self.parse_loaded_editor( result, note_title, revision, link ); }
  );
}

Wiki.prototype.resolve_link = function ( note_title, link, callback ) {
  // if the title looks like a URL, then make it a link to an external site
  if ( /^\w+:\/\//.test( note_title ) ) {
    link.target = "_new";
    link.href = note_title;
    if ( callback ) callback( "web link" );
    return
  }
  link.removeAttribute( "target" );

  var id = parse_query( link ).note_id;

  // if the link already has a valid-looking id, it's already resolved, so bail
  if ( !callback && id != undefined && id != "new" && id != "null" )
    return;

  if ( note_title.length == 0 )
    return;

  // if the note corresponding to the link's title is already open, resolve the link and bail
  var editor = this.open_editors[ note_title ];
  if ( editor ) {
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

Wiki.prototype.parse_loaded_editor = function ( result, note_title, revision, link ) {
  if ( result.note ) {
    var id = result.note.object_id;
    if ( revision ) id += " " + revision;
    var note_text = result.note.contents;
    var deleted_from = result.note.deleted;
    var revisions_list = result.note.revisions_list;
  } else {
    var id = null;
    var note_text = "<h3>" + note_title;
    var deleted_from = null;
    var revisions_list = new Array();
  }

  if ( revision )
    var read_write = false; // show previous revisions as read-only
  else
    var read_write = this.read_write;

  id = this.create_editor( id, note_text, deleted_from, revisions_list, note_title, read_write, true, false );

  // if a link that launched this editor was provided, update it with the created note's id
  if ( link && id )
    link.href = "/notebooks/" + this.notebook_id + "?note_id=" + id;
}

Wiki.prototype.create_editor = function ( id, note_text, deleted_from, revisions_list, note_title, read_write, highlight, focus ) {
  this.clear_messages();

  var self = this;
  if ( isUndefinedOrNull( id ) ) {
    if ( this.read_write ) {
      id = this.next_id;
      this.invoker.invoke( "/next_id", "POST", null,
        function( result ) { self.update_next_id( result ); }
      );
    } else {
      id = 0;
    }
  }

  // for read-only notes within read-write notebooks, tack the revision timestamp onto the start of the note text
  if ( !read_write && this.read_write && revisions_list && revisions_list.length ) {
    var short_revision = this.brief_revision( revisions_list[ revisions_list.length - 1 ] );
    note_text = "<p class=\"small_text\">Previous revision from " + short_revision + "</p>" + note_text;
  }

  var startup = this.startup_notes[ id ];
  var editor = new Editor( id, this.notebook_id, note_text, deleted_from, revisions_list, undefined, read_write, startup, highlight, focus );

  if ( this.read_write ) {
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

  return id;
}

Wiki.prototype.editor_state_changed = function ( editor ) {
  this.update_toolbar();
  this.display_link_pulldown( editor );
}

Wiki.prototype.editor_title_changed = function ( editor, old_title, new_title ) {
  delete this.open_editors[ old_title ];

  if ( new_title != null )
    this.open_editors[ new_title ] = editor;
}

Wiki.prototype.display_link_pulldown = function ( editor ) {
  var link = editor.find_link_at_cursor();

  if ( !link ) {
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
  this.clear_messages();

  if ( editor )
    addElementClass( editor.iframe, "focused_note_frame" );

  if ( this.focused_editor && this.focused_editor != editor ) {
    this.clear_pulldowns();
    removeElementClass( this.focused_editor.iframe, "focused_note_frame" );

    // if the formerly focused editor is completely empty, then remove it as the user leaves it and switches to this editor
    if ( this.focused_editor.empty() ) {
      this.focused_editor.shutdown();
    } else {
      // when switching editors, save the one being left
      this.save_editor( null, fire_and_forget );
    }
  }

  this.focused_editor = editor;
}

Wiki.prototype.editor_key_pressed = function ( editor, event ) {
  var code = event.key().code;
  if ( event.modifier().ctrl ) {
    // ctrl-backtick: alert with frame HTML contents (temporary for debugging)
    if ( code == 192 || code == 96 ) {
      alert( editor.document.body.innerHTML );
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
    // ctrl-n: ordered list
    } else if ( code == 49 ) {
      this.toggle_button( event, "insertOrderedList" );
    // ctrl-l: make a note link
    } else if ( code == 76 ) {
      this.toggle_link_button( event );
    // ctrl-n: new note
    } else if ( code == 78 ) {
      this.create_blank_editor( event );
    // ctrl-h: hide note
    } else if ( code == 72 ) {
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
    addElementClass( button_id, "button_down" );
  else
    removeElementClass( button_id, "button_down" );
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

  if ( this.focused_editor && this.focused_editor.read_write ) {
    this.focused_editor.focus();
    toggleElementClass( "button_down", "createLink" );
    if ( hasElementClass( "createLink", "button_down" ) )
      this.focused_editor.start_link();
    else
      this.focused_editor.end_link();

    this.display_link_pulldown( this.focused_editor );
  }

  event.stop();
}

Wiki.prototype.hide_editor = function ( event, editor ) {
  this.clear_messages();
  this.clear_pulldowns();

  if ( !editor ) {
    editor = this.focused_editor;
    this.focused_editor = null;
  }

  if ( editor ) {
    // before hiding an editor, save it
    if ( this.read_write )
      this.save_editor( editor );

    editor.shutdown();
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

    if ( this.read_write && editor.read_write ) {
      this.invoker.invoke( "/notebooks/delete_note", "POST", { 
        "notebook_id": this.notebook_id,
        "note_id": editor.id
      } );
    }

    if ( editor == this.focused_editor )
      this.focused_editor = null;

    if ( this.notebook.trash && !editor.empty() ) {
      var undo_button = createDOM( "input", {
        "type": "button",
        "class": "message_button",
        "value": "undo",
        "title": "undo deletion"
      } );
      this.display_message( "The note has been moved to the trash.", [ undo_button ] )
      var self = this;
      connect( undo_button, "onclick", function ( event ) { self.undelete_editor_via_undo( event, editor ); } );
    }

    editor.shutdown();
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

    if ( this.read_write && editor.read_write ) {
      this.invoker.invoke( "/notebooks/undelete_note", "POST", { 
        "notebook_id": editor.deleted_from,
        "note_id": editor.id
      } );
    }

    if ( editor == this.focused_editor )
      this.focused_editor = null;

    editor.shutdown();
  }

  event.stop();
}

Wiki.prototype.undelete_editor_via_undo = function( event, editor ) {
  this.clear_messages();
  this.clear_pulldowns();

  if ( editor ) {
    if ( this.read_write && editor.read_write ) {
      this.invoker.invoke( "/notebooks/undelete_note", "POST", { 
        "notebook_id": this.notebook_id,
        "note_id": editor.id
      } );
    }

    this.startup_notes[ editor.id ] = true;
    this.load_editor( "Note not found.", editor.id, null );
  }

  event.stop();
}

Wiki.prototype.compare_versions = function( event, editor, previous_revision ) {
  this.clear_pulldowns();

  // display the two revisions for comparison by the user
  this.load_editor( editor.title, editor.id, previous_revision );
  this.load_editor( editor.title, editor.id );
}

Wiki.prototype.save_editor = function ( editor, fire_and_forget ) {
  if ( !editor )
    editor = this.focused_editor;

  var self = this;
  if ( editor && editor.read_write && !editor.empty() ) {
    var revisions = editor.revisions_list;
    this.invoker.invoke( "/notebooks/save_note", "POST", { 
      "notebook_id": this.notebook_id,
      "note_id": editor.id,
      "contents": editor.contents(),
      "startup": editor.startup,
      "previous_revision": revisions.length ? revisions[ revisions.length - 1 ] : "None"
    }, function ( result ) { self.update_editor_revisions( result, editor ); }, null, fire_and_forget );
  }
}

Wiki.prototype.update_editor_revisions = function ( result, editor ) {
  // if there's not a newly saved revision, then the contents are unchanged, so bail
  if ( !result.new_revision )
    return;

  var revisions = editor.revisions_list;
  var client_previous_revision = revisions.length ? revisions[ revisions.length - 1 ] : null;

  // if the server's idea of the previous revision doesn't match the client's, then someone has
  // gone behind our back and saved the editor's note from another window
  if ( result.previous_revision != client_previous_revision ) {
    var compare_button = createDOM( "input", {
      "type": "button",
      "class": "message_button",
      "value": "compare versions",
      "title": "compare your version with the modified version"
    } );
    this.display_error( 'Your changes to the note titled "' + editor.title + '" have overwritten changes made in another window.', [ compare_button ] );

    var self = this;
    connect( compare_button, "onclick", function ( event ) {
      self.compare_versions( event, editor, result.previous_revision );
    } );

    revisions.push( result.previous_revision );
  }

  // add the new revision to the editor's revisions list
  revisions.push( result.new_revision );
}

Wiki.prototype.search = function ( event ) {
  this.clear_messages();
  this.clear_pulldowns();

  var self = this;
  this.invoker.invoke( "/notebooks/search", "GET", {
      "notebook_id": this.notebook_id,
      "titles_only": this.search_titles_only
    },
    function( result ) { self.display_loaded_notes( result ); },
    "search_form"
  );

  event.stop();
}

Wiki.prototype.toggle_search_options = function ( event ) {
  // if the pulldown is already open, then just close it
  var existing_div = getElement( "search_pulldown" );
  if ( existing_div ) {
    existing_div.pulldown.shutdown();
    return;
  }

  new Search_pulldown( this, this.notebook_id, this.search_titles_only );
  event.stop();
}

Wiki.prototype.display_loaded_notes = function ( result ) {
  // TODO: somehow highlight the search term within the search results?
  // before displaying the search results, save the current focused editor
  this.save_editor();

  // if there are no search results, indicate that and bail
  if ( result.notes.length == 0 ) {
    this.display_error( "No matching notes." );
    return;
  }

  // create an editor for each note search result, focusing the first one
  var focus = true;
  for ( var i in result.notes ) {
    var note = result.notes[ i ]

    // if the editor is already open, just skip it
    var iframe = getElement( "note_" + note.object_id );
    if ( iframe ) {
      iframe.editor.highlight( focus );
      focus = false;
      continue;
    }

    this.create_editor( note.object_id, note.contents, note.deleted_from, note.revisions_list, undefined, this.read_write, focus, focus );
    focus = false;
  }
}

Wiki.prototype.display_message = function ( text, buttons ) {
  this.clear_messages();
  this.clear_pulldowns();

  var inner_div = DIV( { "class": "message_inner" }, text + " " );
  for ( var i in buttons )
    appendChildNodes( inner_div, buttons[ i ] );

  var div = DIV( { "class": "message" }, inner_div );
  div.buttons = buttons;

  appendChildNodes( "notes", div );
  ScrollTo( div );
}

Wiki.prototype.display_error = function ( text, buttons ) {
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
  for ( var i in buttons )
    appendChildNodes( inner_div, buttons[ i ] );

  var div = DIV( { "class": "error" }, inner_div );
  div.buttons = buttons;

  appendChildNodes( "notes", div );
  ScrollTo( div );
}

Wiki.prototype.clear_messages = function () {
  var results = getElementsByTagAndClassName( "div", "message" );

  for ( var i in results ) {
    var result = results[ i ];
    blindUp( result, options = { "duration": 0.5, afterFinish: function () {
      try {
        for ( var j in result.buttons )
          disconnectAll( result.buttons[ j ] );
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
    result.pulldown.shutdown();
  }
}

Wiki.prototype.brief_revision = function ( revision ) {
  return revision.split( /\.\d/ )[ 0 ]; // strip off seconds from the timestamp
}

Wiki.prototype.toggle_editor_changes = function ( event, editor ) {
  // if the pulldown is already open, then just close it
  var pulldown_id = "changes_" + editor.id;
  var existing_div = getElement( pulldown_id );
  if ( existing_div ) {
    existing_div.pulldown.shutdown();
    return;
  }

  new Changes_pulldown( this, this.notebook_id, this.invoker, editor );
  event.stop();
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

connect( window, "onload", function ( event ) { new Wiki(); } );


function Pulldown( wiki, notebook_id, pulldown_id, anchor, relative_to ) {
  this.wiki = wiki;
  this.notebook_id = notebook_id;
  this.div = createDOM( "div", { "id": pulldown_id, "class": "pulldown" } );
  this.div.pulldown = this;
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
  
  // display list of revision timestamps in reverse chronological order
  if ( isUndefinedOrNull( this.editor.revisions_list ) || this.editor.revisions_list.length == 0 ) {
    appendChildNodes( this.div, createDOM( "span", "This note has no previous changes." ) );
    return;
  }

  var revisions_list = clone( this.editor.revisions_list );
  revisions_list.reverse();

  var self = this;
  for ( var i = 0; i < revisions_list.length; ++i ) {
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
  this.wiki.load_editor( "Revision not found.", note_id, revision );
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
    self.title_field.value = link.href;
    replaceChildNodes( self.note_preview, "web link" );
    return;
  }

  // if the note has no destination note id set, try loading the note from the server by title
  var query = parse_query( link );
  var title = link_title( link, query );
  var id = query.note_id;
  if ( ( id == undefined || id == "new" || id == "null" ) && title.length > 0 ) {
    this.invoker.invoke(
      "/notebooks/load_note_by_title", "GET", {
        "notebook_id": this.notebook_id,
        "note_title": title
      },
      function ( result ) {
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


function Search_pulldown( wiki, notebook_id, titles_only ) {
  Pulldown.call( this, wiki, notebook_id, "search_pulldown", getElement( "search_button" ) );

  this.titles_radio = createDOM( "input", { "type": "radio", "class": "pulldown_radio" } );
  this.titles_toggle = createDOM( "a", { "href": "", "class": "pulldown_link", "title": "Search only note titles." },
    "titles only"
  );
  this.everything_radio = createDOM( "input", { "type": "radio", "class": "pulldown_radio" } );
  this.everything_toggle = createDOM( "a", { "href": "", "class": "pulldown_link", "title": "Search everything, including note titles and contents." },
    "everything"
  );

  appendChildNodes( this.div, this.titles_radio );
  appendChildNodes( this.div, this.titles_toggle );
  appendChildNodes( this.div, createDOM( "br" ) );
  appendChildNodes( this.div, this.everything_radio );
  appendChildNodes( this.div, this.everything_toggle );

  if ( titles_only )
    this.titles_radio.checked = true;
  else
    this.everything_radio.checked = true;

  var self = this;
  connect( this.titles_radio, "onclick", function ( event ) { self.titles_clicked( event ); } );
  connect( this.titles_toggle, "onclick", function ( event ) { self.titles_clicked( event ); } );
  connect( this.everything_radio, "onclick", function ( event ) { self.everything_clicked( event ); } );
  connect( this.everything_toggle, "onclick", function ( event ) { self.everything_clicked( event ); } );
}

Search_pulldown.prototype = new function () { this.prototype = Pulldown.prototype; };
Search_pulldown.prototype.constructor = Search_pulldown;

Search_pulldown.prototype.titles_clicked = function ( event ) {
  if ( event.target() != this.titles_radio )
    this.titles_radio.checked = true;
  this.everything_radio.checked = false;
  this.wiki.search_titles_only = true;
  event.stop();
}

Search_pulldown.prototype.everything_clicked = function ( event ) {
  if ( event.target() != this.everything_radio )
    this.everything_radio.checked = true;
  this.titles_radio.checked = false;
  this.wiki.search_titles_only = false;
  event.stop();
}

Search_pulldown.prototype.shutdown = function () {
  Pulldown.prototype.shutdown.call( this );

  disconnectAll( this.titles_radio );
  disconnectAll( this.titles_toggle );
  disconnectAll( this.everything_radio );
  disconnectAll( this.everything_toggle );
}
