function Wiki() {
  this.next_id = null;
  this.focused_editor = null;
  this.blank_editor_id = null;
  this.notebook = null;
  this.notebook_id = getElement( "notebook_id" ).value;
  this.read_write = false;
  this.startup_notes = new Array(); // map of startup notes: note id to bool
  this.invoker = new Invoker();

  connect( this.invoker, "error_message", this, "display_message" );
  connect( "search_form", "onsubmit", this, "search" );

  // get info on the requested notebook (if any)
  var self = this;
  if ( this.notebook_id ) {
    this.invoker.invoke(
      "/notebooks/contents", "GET", {
        "notebook_id": this.notebook_id
      },
      function( result ) { self.populate( result ); }
    );
  }

  // get info on the current user (logged-in or anonymous)
  this.invoker.invoke( "/users/current", "GET", null,
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
    this.populate( { "notebook" : result.notebooks[ 0 ] } );
  }

  if ( result.user.username == "anonymous" )
    return;

  // display links for current notebook a list of other notebooks that the user has access to
  var span = createDOM( "span" );
  replaceChildNodes( "notebook_area", span );
  appendChildNodes( span, createDOM( "a", { "href": "/notebooks/" + this.notebook_id, "id": "recent_notes_link" }, "recent notes" ) );
  appendChildNodes( span, createDOM( "br" ) );
  appendChildNodes( span, createDOM( "a", { "href": "/notebooks/download_html/" + this.notebook_id, "id": "download_html_link" }, "download as html" ) );

  appendChildNodes( span, createDOM( "h3", "other notebooks" ) );
  for ( var i in result.notebooks ) {
    var notebook = result.notebooks[ i ];
    if ( notebook.object_id != this.notebook_id ) {
      appendChildNodes( span, createDOM( "a", {
        "href": ( notebook.name == "Luminotes" ) ? "/" : "/notebooks/" + notebook.object_id,
        "id": "notebook_" + notebook.object_id
      }, notebook.name ) );
      appendChildNodes( span, createDOM( "br" ) );
    }
  }

  // display the name of the logged in user and a logout link
  span = createDOM( "span" );
  replaceChildNodes( "user_area", span );
  appendChildNodes( span, "logged in as " + result.user.username );
  appendChildNodes( span, " | " );
  appendChildNodes( span, createDOM( "a", { "href": "/", "id": "logout_link" }, "logout" ) );

  var self = this;
  connect( "recent_notes_link", "onclick", function ( event ) {
    self.invoker.invoke(
      "/notebooks/recent_notes", "GET", { "notebook_id": self.notebook_id },
      function( result ) { self.display_search_results( result ); }
    );
    event.stop();
  } );


  connect( "download_html_link", "onclick", function ( event ) {
    self.save_editor( null, true );
  } );

  connect( "logout_link", "onclick", function ( event ) {
    self.save_editor( null, true );
    self.invoker.invoke( "/users/logout", "POST" );
    event.stop();
  } );
}

Wiki.prototype.populate = function ( result ) {
  this.notebook = result.notebook;
  var self = this;

  if ( this.notebook.name != "Luminotes" )
    replaceChildNodes( "notebook_name", createDOM( "h3", this.notebook.name ) );
  
  if ( this.notebook.read_write ) {
    this.read_write = true;
    removeElementClass( "toolbar", "undisplayed" );

    connect( window, "onunload", function ( event ) { self.editor_focused( null, true ); } );
    connect( "bold", "onclick", function ( event ) { self.toggle_button( event, "bold" ); } );
    connect( "italic", "onclick", function ( event ) { self.toggle_button( event, "italic" ); } );
    connect( "title", "onclick", function ( event ) { self.toggle_button( event, "title", "h3" ); } );
    connect( "insertUnorderedList", "onclick", function ( event ) { self.toggle_button( event, "insertUnorderedList" ); } );
    connect( "insertOrderedList", "onclick", function ( event ) { self.toggle_button( event, "insertOrderedList" ); } );
    connect( "createLink", "onclick", this, "toggle_link_button" );
    connect( "newNote", "onclick", this, "create_blank_editor" );
    connect( "html", "onclick", this, "background_clicked" );

    // grab the next available object id
    this.invoker.invoke( "/next_id", "POST", null,
      function( result ) { self.update_next_id( result ); }
    );
  }

  // create an editor for each startup note in the received notebook, focusing the first one
  for ( var i in this.notebook.startup_notes ) {
    var note = this.notebook.startup_notes[ i ];
    if ( !note ) continue;
    this.startup_notes[ note.object_id ] = true;
    var focus = ( i == 0 );
    this.create_editor( note.object_id, note.contents, undefined, undefined, false, focus );
  }
}

Wiki.prototype.background_clicked = function ( event ) {
  this.clear_pulldowns();

  // unless a background div was clicked, bail
  var node_name = event.target().nodeName.toLowerCase();
  if ( node_name != "div" && node_name != "html" )
    return;

  this.create_blank_editor( event );
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

  this.blank_editor_id = this.create_editor( undefined, undefined, undefined, undefined, true, true );
}

Wiki.prototype.load_editor = function ( note_title, insert_after_iframe_id, note_id ) {
  var self = this;

  this.invoker.invoke(
    "/notebooks/load_note", "GET", {
      "notebook_id": this.notebook_id,
      "note_id": note_id
    },
    function ( result ) { self.parse_loaded_editor( result, insert_after_iframe_id, note_title ); }
  );
}

Wiki.prototype.load_editor_by_title = function ( note_title, insert_after_iframe_id ) {
  var self = this;

  this.invoker.invoke(
    "/notebooks/load_note_by_title", "GET", {
      "notebook_id": this.notebook_id,
      "note_title": note_title
    },
    function ( result ) { self.parse_loaded_editor( result, insert_after_iframe_id, note_title ); }
  );
}

Wiki.prototype.parse_loaded_editor = function ( result, insert_after_iframe_id, note_title ) {
  if ( result.note ) {
    var id = result.note.object_id
    var note_text = result.note.contents;
  } else {
    var id = null;
    var note_text = "<h3>" + note_title;
  }

  this.create_editor( id, note_text, insert_after_iframe_id, note_title, true, false );
}

Wiki.prototype.create_editor = function ( id, note_text, insert_after_iframe_id, note_title, highlight, focus ) {
  this.clear_messages();
  this.clear_pulldowns();

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

  // update any matching links in insert_after_iframe_id with the id of this new editor
  if ( insert_after_iframe_id ) {
    var links = getElementsByTagAndClassName( "a", null, getElement( insert_after_iframe_id ).editor.document );
    for ( var i in links ) {
      // a link matches if its contained text is the same as this note's title
      if ( scrapeText( links[ i ] ) == note_title )
        links[ i ].href = "/notes/" + id;
    }
  }

  // if an iframe has been given to insert this new editor after, then hide all subsequent non-startup editors
  if ( insert_after_iframe_id ) {
    var sibling = getElement( insert_after_iframe_id ).nextSibling;
    while ( sibling ) {
      var nextSibling = sibling.nextSibling;

      if ( sibling.editor && ( this.read_write || !sibling.editor.startup ) )
        sibling.editor.shutdown();

      sibling = nextSibling;
    }
  }

  var startup = this.startup_notes[ id ];
  var editor = new Editor( id, note_text, undefined, this.read_write, startup, highlight, focus );

  if ( this.read_write ) {
    connect( editor, "state_changed", this, "editor_state_changed" );
    connect( editor, "key_pressed", this, "editor_key_pressed" );
    connect( editor, "delete_clicked", function ( event ) { self.delete_editor( event, editor ) } );
    connect( editor, "options_clicked", function ( event ) { self.toggle_editor_options( event, editor ) } );
    connect( editor, "focused", this, "editor_focused" );
  }

  connect( editor, "load_editor", this, "load_editor" );
  connect( editor, "load_editor_by_title", this, "load_editor_by_title" );
  connect( editor, "hide_clicked", function ( event ) { self.hide_editor( event, editor ) } );
  connect( editor, "submit_form", function ( url, form ) {
    self.invoker.invoke( url, "POST", null, null, form );
  } );

  return id;
}

Wiki.prototype.editor_state_changed = function ( editor ) {
  this.update_toolbar();
}

Wiki.prototype.editor_focused = function ( editor, fire_and_forget ) {
  this.clear_messages();
  this.clear_pulldowns();

  if ( editor )
    addElementClass( editor.iframe, "focused_note_frame" );

  if ( this.focused_editor && this.focused_editor != editor ) {
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
    // ctrl-t: title
    } else if ( code == 84 ) {
      this.toggle_button( event, "title", "h3" );
    // ctrl-u: unordered list
    } else if ( code == 85 ) {
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

  if ( this.focused_editor ) {
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
    this.update_button( "title", "h3" );
    this.update_button( "insertUnorderedList" );
    this.update_button( "insertOrderedList" );
    this.update_button( "createLink" );
  }
}

Wiki.prototype.toggle_link_button = function ( event ) {
  this.clear_messages();
  this.clear_pulldowns();

  if ( this.focused_editor ) {
    this.focused_editor.focus();
    toggleElementClass( "button_down", "createLink" );
    if ( hasElementClass( "createLink", "button_down" ) )
      this.focused_editor.start_link();
    else
      this.focused_editor.end_link();
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

    if ( this.read_write ) {
      this.invoker.invoke( "/notebooks/delete_note", "POST", { 
        "notebook_id": this.notebook_id,
        "note_id": editor.id
      } );
    }

    if ( editor == this.focused_editor )
      this.focused_editor = null;

    editor.shutdown();
  }

  event.stop();
}

Wiki.prototype.save_editor = function ( editor, fire_and_forget ) {
  if ( !editor )
    editor = this.focused_editor;

  if ( editor && !editor.empty() ) {
    // TODO: do something with the result other than just ignoring it
    this.invoker.invoke( "/notebooks/save_note", "POST", { 
      "notebook_id": this.notebook_id,
      "note_id": editor.id,
      "contents": editor.contents(),
      "startup": editor.startup
    }, null, null, fire_and_forget );
  }
}

Wiki.prototype.search = function ( event ) {
  this.clear_messages();
  this.clear_pulldowns();

  var self = this;
  this.invoker.invoke( "/notebooks/search", "GET", { "notebook_id": this.notebook_id },
    function( result ) { self.display_search_results( result ); },
    "search_form"
  );

  event.stop();
}

Wiki.prototype.display_search_results = function ( result ) {
  // TODO: somehow highlight the search term within the search results?
  // before displaying the search results, save the current focused editor
  this.save_editor();

  // if there are no search results, indicate that and bail
  if ( result.notes.length == 0 ) {
    this.display_message( "No matching notes." );
    return;
  }

  // create an editor for each note search result, focusing the first one
  for ( var i in result.notes ) {
    var note = result.notes[ i ]
    var focus = ( i == 0 );

    // if the editor is already open, just move it down to be with the result of the search results
    var iframe = getElement( "note_" + note.object_id );
    if ( iframe ) {
      removeElement( iframe.editor.note_controls );
      removeElement( iframe );
      appendChildNodes( "notes", iframe.editor.note_controls );
      appendChildNodes( "notes", iframe );
      iframe.editor.highlight( focus );
      continue;
    }

    this.create_editor( note.object_id, note.contents, undefined, undefined, false, focus );
  }
}

Wiki.prototype.display_message = function ( text ) {
  this.clear_messages();
  this.clear_pulldowns();

  var inner_div = DIV( { "class": "message_inner" }, text );
  var div = DIV( { "class": "message" }, inner_div );
  appendChildNodes( "notes", div );
  ScrollTo( div );
}

Wiki.prototype.clear_messages = function () {
  var results = getElementsByTagAndClassName( "div", "message" );

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

Wiki.prototype.toggle_editor_options = function ( event, editor ) {
  // if the pulldown is already open, then just close it
  var pulldown_id = "options_" + editor.id;
  var existing_div = getElement( pulldown_id );
  if ( existing_div ) {
    existing_div.pulldown.shutdown();
    return;
  }

  new Options_pulldown( this.notebook_id, this.invoker, editor );
  event.stop();
}

connect( window, "onload", function ( event ) { new Wiki(); } );


function Pulldown( notebook_id, pulldown_id, button ) {
  this.notebook_id = notebook_id;
  this.div = createDOM( "div", { "id": pulldown_id, "class": "pulldown" } );
  this.div.pulldown = this;
  addElementClass( this.div, "invisible" );

  this.close_button = createDOM( "input", { "type": "button", "value": " x ", "class": "pulldown_button" } );

  appendChildNodes( this.div, this.close_button );
  appendChildNodes( document.body, this.div );

  var self = this;
  connect( this.close_button, "onclick", function ( event ) { self.shutdown(); event.stop(); } );

  // position the pulldown under the button that opened it
  var position = getElementPosition( button );
  var button_dimensions = getElementDimensions( button );
  var div_dimensions = getElementDimensions( this.div );
  position.x -= div_dimensions.w - button_dimensions.w;
  position.y += button_dimensions.h;
  setElementPosition( this.div, position );

  removeElementClass( this.div, "invisible" );
} 

Pulldown.prototype.shutdown = function () {
  disconnectAll( this.close_button );
  removeElement( this.div );
}


Options_pulldown = function ( notebook_id, invoker, editor ) {
  Pulldown.call( this, notebook_id, "options_" + editor.id, editor.options_button );

  this.invoker = invoker;
  this.editor = editor;
  this.startup_checkbox = createDOM( "input", { "type": "checkbox" } );
  this.startup_toggle = createDOM( "span", { "class": "pulldown_toggle" },
    this.startup_checkbox,
    "show on startup"
  );

  appendChildNodes( this.div, this.startup_toggle );
  this.startup_checkbox.checked = editor.startup;

  var self = this;
  connect( this.startup_toggle, "onclick", function ( event ) { self.startup_clicked( event ); event.stop(); } );
}

Options_pulldown.prototype = Pulldown;
Options_pulldown.prototype.constructor = Options_pulldown;

Options_pulldown.prototype.startup_clicked = function ( event ) {
  if ( event.target() != this.startup_checkbox )
    this.startup_checkbox.checked = this.startup_checkbox.checked ? false : true;
  this.editor.startup = this.startup_checkbox.checked;

  // if this note isn't empty, save it along with its startup status
  if ( !this.editor.empty() ) {
    this.invoker.invoke( "/notebooks/save_note", "POST", { 
      "notebook_id": this.notebook_id,
      "note_id": this.editor.id,
      "contents": this.editor.contents(),
      "startup": this.editor.startup
    } );
  }
}

Options_pulldown.prototype.shutdown = function () {
  Pulldown.prototype.shutdown.call( this );

  disconnectAll( this.startup_toggle );
}
