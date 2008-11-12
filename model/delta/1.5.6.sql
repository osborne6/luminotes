-- Before this will execute, you need to run the following command as the
-- PostgreSQL superuser (usually "postgres"):
--   echo "create language plpgsql;" | psql luminotes
create function log_note_revision() returns trigger as $_$
  begin
    insert into note values
      ( NEW.id, NEW.revision, NEW.title, NEW.contents, NEW.notebook_id, NEW.startup,
        NEW.deleted_from_id, NEW.rank, NEW.user_id );
    return null;
  end;
  $_$ language plpgsql;
create index session_id_index on session using btree (id);
create index note_user_id_index on note USING btree (user_id);
CREATE TABLE note_current_new (
    id text NOT NULL,
    revision timestamp with time zone NOT NULL,
    title text,
    contents text,
    notebook_id text,
    startup boolean DEFAULT false,
    deleted_from_id text,
    rank numeric,
    search tsvector,
    user_id text
);
insert into note_current_new select * from note_current;
drop view note_current;
alter table note_current_new rename to note_current;
ALTER TABLE ONLY note_current ADD CONSTRAINT note_current_pkey PRIMARY KEY (id);
CREATE INDEX note_current_notebook_id_index ON note_current USING btree (notebook_id);
CREATE INDEX note_current_notebook_id_startup_index ON note_current USING btree (notebook_id, startup);
CREATE INDEX note_current_notebook_id_title_index ON note_current USING btree (notebook_id, md5(title));
create index note_current_user_id_index on note_current USING btree (user_id);
drop trigger search_update on note;
drop index search_index;
alter table note drop column search;
update note_current set search = to_tsvector('default', coalesce(title,'') ||' '|| coalesce(contents,'') );
commit;
vacuum full analyze;
start transaction;
create index note_current_search_index on note_current USING gist (search);
commit;
vacuum full analyze;
start transaction;
CREATE TRIGGER search_update
  BEFORE INSERT OR UPDATE ON note_current
  FOR EACH ROW
  EXECUTE PROCEDURE tsearch2('search', 'drop_html_tags', 'title', 'contents');
CREATE TRIGGER note_current_update
  AFTER INSERT OR UPDATE ON note_current
  FOR EACH ROW
  EXECUTE PROCEDURE log_note_revision();
