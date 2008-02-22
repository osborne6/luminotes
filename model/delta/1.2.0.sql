create table file (
  id text,
  revision timestamp with time zone,
  notebook_id text,
  note_id text,
  filename text,
  size_bytes integer,
  content_type text
);
alter table file add primary key ( id );
create index file_note_id_index on file using btree ( note_id );
