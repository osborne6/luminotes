function setUpPage() {
  id = "fake_id";
  notebook_id = "fake_notebook_id";
  title = "the title"
  note_text = "<h3>" + title + "</h3>blah";
  deleted_from_id = undefined;
  revisions_list = undefined;
  read_write = true;
  startup = false;
  highlight = false;
  editor_focus = false;

  editor = new Editor( id, notebook_id, note_text, deleted_from_id, revisions_list, read_write, startup, highlight, editor_focus );

  init_complete = false;
  connect( editor, "init_complete", function () { init_complete = true; } );

  wait_for_init_complete();
}

function wait_for_init_complete() {
  // busywait for the editor initialization to complete
  if ( !init_complete ) {
    setTimeout( "wait_for_init_complete()", 10 );
    return;
  }

  setUpPageStatus = "complete";
}

function tearDownPage() {
  editor.shutdown();
}
