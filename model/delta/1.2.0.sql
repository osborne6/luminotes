create table file (
  id text,
  revision timestamp with time zone,
  notebook_id text,
  note_id text,
  filename text,
  size_bytes integer
);
alter table file add primary key ( id );
