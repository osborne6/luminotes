update notebook set user_id = (
  select user_notebook.user_id
    from user_notebook
    where notebook_id = notebook.id and read_write = 't' and owner = 't'
    limit 1
);
update note set user_id = (
  select notebook_current.user_id
    from notebook_current
    where note.notebook_id = notebook_current.id
);
