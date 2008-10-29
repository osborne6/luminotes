--
-- PostgreSQL database schema
--

SET client_encoding = 'UTF8';
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

CREATE FUNCTION drop_html_tags(text) RETURNS text
    AS $_$select regexp_replace( regexp_replace( $1, '</?(div|p|br|ul|ol|li|h3)( [^>]*?)?/?>', ' ', 'gi' ), '<[^>]+?>', '', 'g' );$_$
    LANGUAGE sql;
ALTER FUNCTION public.drop_html_tags(text) OWNER TO luminotes;
CREATE TABLE file (
    id text NOT NULL,
    revision timestamp with time zone,
    notebook_id text,
    note_id text,
    filename text,
    size_bytes integer,
    content_type text
);
ALTER TABLE public.file OWNER TO luminotes;
CREATE TABLE tag (
    id text NOT NULL,
    revision timestamp with time zone,
    notebook_id text,
    user_id text,
    name text,
    description text
);
ALTER TABLE public.tag OWNER TO luminotes;
CREATE TABLE tag_notebook (
    notebook_id text,
    tag_id text,
    value text,
    user_id text
);

ALTER TABLE public.tag_notebook OWNER TO luminotes;
CREATE TABLE tag_note (
    note_id text,
    tag_id text,
    value text
);
ALTER TABLE public.tag_note OWNER TO luminotes;
CREATE TABLE invite (
    id text NOT NULL,
    revision timestamp with time zone NOT NULL,
    from_user_id text,
    notebook_id text,
    email_address text,
    read_write boolean,
    "owner" boolean,
    redeemed_user_id text
);
ALTER TABLE public.invite OWNER TO luminotes;
CREATE TABLE luminotes_group (
    id text NOT NULL,
    revision timestamp with time zone NOT NULL,
    name text
);
ALTER TABLE public.luminotes_group OWNER TO luminotes;
CREATE VIEW luminotes_group_current AS
    SELECT luminotes_group.id, luminotes_group.revision, luminotes_group.name FROM luminotes_group WHERE (luminotes_group.revision IN (SELECT max(sub_group.revision) AS max FROM luminotes_group sub_group WHERE (sub_group.id = luminotes_group.id)));
ALTER TABLE public.luminotes_group_current OWNER TO luminotes;
CREATE TABLE luminotes_user (
    id text NOT NULL,
    revision timestamp with time zone NOT NULL,
    username text,
    salt text,
    password_hash text,
    email_address text,
    storage_bytes integer,
    rate_plan integer
);
ALTER TABLE public.luminotes_user OWNER TO luminotes;
CREATE VIEW luminotes_user_current AS
    SELECT luminotes_user.id, luminotes_user.revision, luminotes_user.username, luminotes_user.salt, luminotes_user.password_hash, luminotes_user.email_address, luminotes_user.storage_bytes, luminotes_user.rate_plan FROM luminotes_user WHERE (luminotes_user.revision IN (SELECT max(sub_user.revision) AS max FROM luminotes_user sub_user WHERE (sub_user.id = luminotes_user.id)));
ALTER TABLE public.luminotes_user_current OWNER TO luminotes;
CREATE TABLE note (
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
ALTER TABLE public.note OWNER TO luminotes;
CREATE VIEW note_current AS
    SELECT note.id, note.revision, note.title, note.contents, note.notebook_id, note.startup, note.deleted_from_id, note.rank, note.search, note.user_id FROM note WHERE (note.revision IN (SELECT max(sub_note.revision) AS max FROM note sub_note WHERE (sub_note.id = note.id)));
ALTER TABLE public.note_current OWNER TO luminotes;
CREATE TABLE notebook (
    id text NOT NULL,
    revision timestamp with time zone NOT NULL,
    name text,
    trash_id text,
    deleted boolean DEFAULT false,
    user_id text
);
ALTER TABLE public.notebook OWNER TO luminotes;
CREATE VIEW notebook_current AS
    SELECT notebook.id, notebook.revision, notebook.name, notebook.trash_id, notebook.deleted, notebook.user_id FROM notebook WHERE (notebook.revision IN (SELECT max(sub_notebook.revision) AS max FROM notebook sub_notebook WHERE (sub_notebook.id = notebook.id)));
ALTER TABLE public.notebook_current OWNER TO luminotes;
CREATE TABLE password_reset (
    id text NOT NULL,
    revision timestamp with time zone NOT NULL,
    email_address text,
    redeemed boolean
);
ALTER TABLE public.password_reset OWNER TO luminotes;

CREATE TABLE download_access (
    id text NOT NULL,
    revision timestamp with time zone NOT NULL,
    item_number text,
    transaction_id text
);
ALTER TABLE public.download_access OWNER TO luminotes;
CREATE TABLE user_group (
    user_id text NOT NULL,
    group_id text NOT NULL,
    "admin" boolean DEFAULT false
);
ALTER TABLE public.user_group OWNER TO luminotes;
CREATE TABLE user_notebook (
    user_id text NOT NULL,
    notebook_id text NOT NULL,
    read_write boolean DEFAULT false,
    "owner" boolean DEFAULT false,
    rank numeric,
    own_notes_only boolean DEFAULT false
);
ALTER TABLE public.user_notebook OWNER TO luminotes;
CREATE TABLE session (
    id text,
    data text,
    expiration_time timestamp
);
ALTER TABLE public.session OWNER TO luminotes;


ALTER TABLE ONLY file
    ADD CONSTRAINT file_pkey PRIMARY KEY (id);

ALTER TABLE ONLY tag
    ADD CONSTRAINT tag_pkey PRIMARY KEY (id);

ALTER TABLE ONLY tag_notebook
    ADD CONSTRAINT tag_notebook_pkey PRIMARY KEY (user_id, notebook_id, tag_id);

ALTER TABLE ONLY tag_note
    ADD CONSTRAINT tag_note_pkey PRIMARY KEY (note_id, tag_id);

ALTER TABLE ONLY invite
    ADD CONSTRAINT invite_pkey PRIMARY KEY (id);

ALTER TABLE ONLY luminotes_user
    ADD CONSTRAINT luminotes_user_pkey PRIMARY KEY (id, revision);

ALTER TABLE ONLY note
    ADD CONSTRAINT note_pkey PRIMARY KEY (id, revision);

ALTER TABLE ONLY notebook
    ADD CONSTRAINT notebook_pkey PRIMARY KEY (id, revision);

ALTER TABLE ONLY password_reset
    ADD CONSTRAINT password_reset_pkey PRIMARY KEY (id);

ALTER TABLE ONLY download_access
    ADD CONSTRAINT download_access_pkey PRIMARY KEY (id);

ALTER TABLE ONLY user_notebook
    ADD CONSTRAINT user_notebook_pkey PRIMARY KEY (user_id, notebook_id);

CREATE INDEX file_note_id_index ON file USING btree (note_id);

CREATE INDEX file_notebook_id_index ON file USING btree (notebook_id);

CREATE INDEX tag_notebook_id_index ON tag USING btree (notebook_id);

CREATE INDEX tag_user_id_index ON tag USING btree (user_id);

CREATE INDEX luminotes_group_pkey ON luminotes_group USING btree (id, revision);

CREATE INDEX luminotes_user_email_address_index ON luminotes_user USING btree (email_address);

CREATE INDEX luminotes_user_username_index ON luminotes_user USING btree (username);

CREATE INDEX note_notebook_id_index ON note USING btree (notebook_id);

CREATE INDEX note_notebook_id_startup_index ON note USING btree (notebook_id, startup);

CREATE INDEX note_notebook_id_title_index ON note USING btree (notebook_id, md5(title));

CREATE INDEX password_reset_email_address_index ON password_reset USING btree (email_address);

CREATE INDEX download_access_transaction_id_index ON download_access USING btree (transaction_id);

CREATE INDEX search_index ON note USING gist (search);

CREATE TRIGGER search_update
    BEFORE INSERT OR UPDATE ON note
    FOR EACH ROW
    EXECUTE PROCEDURE tsearch2('search', 'drop_html_tags', 'title', 'contents');

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;
