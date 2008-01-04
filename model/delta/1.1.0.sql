update notebook set user_id = user_notebook.user_id
  from user_notebook
  where user_notebook.notebook_id = notebook.id and read_write = 't' and owner = 't';
update note set user_id = notebook_current.user_id
  from notebook_current
  where note.notebook_id = notebook_current.id;
