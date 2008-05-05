drop index note_notebook_id_title_index;
create index note_notebook_id_title_index on note using btree ( notebook_id, md5( title ) );
