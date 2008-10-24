create table tag (
  id text,
  revision timestamp with time zone,
  notebook_id text,
  user_id text,
  name text,
  description text
);
ALTER TABLE ONLY tag ADD CONSTRAINT tag_pkey PRIMARY KEY (id);
CREATE INDEX tag_notebook_id_index ON tag USING btree (notebook_id);
CREATE INDEX tag_user_id_index ON tag USING btree (user_id);

create table tag_notebook (
  notebook_id text,
  tag_id text,
  value text,
  user_id text
);
ALTER TABLE ONLY tag_notebook ADD CONSTRAINT tag_notebook_pkey PRIMARY KEY (user_id, notebook_id, tag_id);

create table tag_note (
  note_id text,
  tag_id text,
  value text
);
ALTER TABLE ONLY tag_note ADD CONSTRAINT tag_note_pkey PRIMARY KEY (note_id, tag_id);

ALTER TABLE user_notebook ADD COLUMN own_notes_only boolean DEFAULT false;

update user_notebook set rank = 0 from luminotes_user_current, notebook_current where user_notebook.user_id = luminotes_user_current.id and username = 'anonymous' and user_notebook.notebook_id = notebook_current.id and notebook_current.name = 'Luminotes'; 
