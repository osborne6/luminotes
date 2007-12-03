create table invite (
  id text not null,
  revision timestamp with time zone not null,
  from_user_id text,
  notebook_id text,
  email_address text,
  read_write boolean,
  owner boolean,
  redeemed_user_id text
);
alter table invite add primary key ( id );
alter table user_notebook add column owner boolean default false;
update user_notebook set owner = 't' where read_write = 't';
alter table notebook add column user_id text;
alter table note add column user_id text;
drop view notebook_current;
create view notebook_current as SELECT id, revision, name, trash_id, deleted, user_id
  from notebook
  where ( notebook.revision IN ( SELECT max( sub_notebook.revision ) AS max FROM notebook sub_notebook
  where sub_notebook.id = notebook.id ) );
drop view note_current;
create view note_current as select id, revision, title, contents, notebook_id, startup, deleted_from_id, rank, search, user_id
  from note where ( note.revision in ( select max( sub_note.revision ) as max from note sub_note where sub_note.id = note.id ) );
