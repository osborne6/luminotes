--
-- PostgreSQL database dump
--

SET client_encoding = 'UTF8';
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS 'Standard public schema';


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;


--
-- Name: drop_html_tags(text); Type: FUNCTION; Schema: public; Owner: luminotes
--

CREATE FUNCTION drop_html_tags(text) RETURNS text
    AS $_$select regexp_replace( regexp_replace( $1, '</?(div|p|br|ul|ol|li|h3)( [^>]*?)?>', ' ', 'gi' ), '<[^>]+?>', '', 'g' );$_$
    LANGUAGE sql;


ALTER FUNCTION public.drop_html_tags(text) OWNER TO luminotes;

--
-- Name: luminotes_user; Type: TABLE; Schema: public; Owner: luminotes; Tablespace: 
--

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

--
-- Name: luminotes_user_current; Type: VIEW; Schema: public; Owner: luminotes
--

CREATE VIEW luminotes_user_current AS
    SELECT luminotes_user.id, luminotes_user.revision, luminotes_user.username, luminotes_user.salt, luminotes_user.password_hash, luminotes_user.email_address, luminotes_user.storage_bytes, luminotes_user.rate_plan FROM luminotes_user WHERE (luminotes_user.revision IN (SELECT max(sub_user.revision) AS max FROM luminotes_user sub_user WHERE (sub_user.id = luminotes_user.id)));


ALTER TABLE public.luminotes_user_current OWNER TO luminotes;

--
-- Name: note; Type: TABLE; Schema: public; Owner: luminotes; Tablespace: 
--

CREATE TABLE note (
    id text NOT NULL,
    revision timestamp with time zone NOT NULL,
    title text,
    contents text,
    notebook_id text,
    startup boolean DEFAULT false,
    deleted_from_id text,
    rank numeric,
    search tsvector
);


ALTER TABLE public.note OWNER TO luminotes;

--
-- Name: note_current; Type: VIEW; Schema: public; Owner: luminotes
--

CREATE VIEW note_current AS
    SELECT note.id, note.revision, note.title, note.contents, note.notebook_id, note.startup, note.deleted_from_id, note.rank, note.search FROM note WHERE (note.revision IN (SELECT max(sub_note.revision) AS max FROM note sub_note WHERE (sub_note.id = note.id)));


ALTER TABLE public.note_current OWNER TO luminotes;

--
-- Name: notebook; Type: TABLE; Schema: public; Owner: luminotes; Tablespace: 
--

CREATE TABLE notebook (
    id text NOT NULL,
    revision timestamp with time zone NOT NULL,
    name text,
    trash_id text
);


ALTER TABLE public.notebook OWNER TO luminotes;

--
-- Name: notebook_current; Type: VIEW; Schema: public; Owner: luminotes
--

CREATE VIEW notebook_current AS
    SELECT notebook.id, notebook.revision, notebook.name, notebook.trash_id FROM notebook WHERE (notebook.revision IN (SELECT max(sub_notebook.revision) AS max FROM notebook sub_notebook WHERE (sub_notebook.id = notebook.id)));


ALTER TABLE public.notebook_current OWNER TO luminotes;

--
-- Name: password_reset; Type: TABLE; Schema: public; Owner: luminotes; Tablespace: 
--

CREATE TABLE password_reset (
    id text NOT NULL,
    revision timestamp with time zone NOT NULL,
    email_address text,
    redeemed boolean
);


ALTER TABLE public.password_reset OWNER TO luminotes;

--
-- Name: user_notebook; Type: TABLE; Schema: public; Owner: luminotes; Tablespace: 
--

CREATE TABLE user_notebook (
    user_id text NOT NULL,
    notebook_id text NOT NULL,
    read_write boolean DEFAULT false
);


ALTER TABLE public.user_notebook OWNER TO luminotes;

--
-- Name: luminotes_user_pkey; Type: CONSTRAINT; Schema: public; Owner: luminotes; Tablespace: 
--

ALTER TABLE ONLY luminotes_user
    ADD CONSTRAINT luminotes_user_pkey PRIMARY KEY (id, revision);


--
-- Name: note_pkey; Type: CONSTRAINT; Schema: public; Owner: luminotes; Tablespace: 
--

ALTER TABLE ONLY note
    ADD CONSTRAINT note_pkey PRIMARY KEY (id, revision);


--
-- Name: notebook_pkey; Type: CONSTRAINT; Schema: public; Owner: luminotes; Tablespace: 
--

ALTER TABLE ONLY notebook
    ADD CONSTRAINT notebook_pkey PRIMARY KEY (id, revision);


--
-- Name: password_reset_pkey; Type: CONSTRAINT; Schema: public; Owner: luminotes; Tablespace: 
--

ALTER TABLE ONLY password_reset
    ADD CONSTRAINT password_reset_pkey PRIMARY KEY (id);


--
-- Name: user_notebook_pkey; Type: CONSTRAINT; Schema: public; Owner: luminotes; Tablespace: 
--

ALTER TABLE ONLY user_notebook
    ADD CONSTRAINT user_notebook_pkey PRIMARY KEY (user_id, notebook_id);


--
-- Name: luminotes_user_email_address_index; Type: INDEX; Schema: public; Owner: luminotes; Tablespace: 
--

CREATE INDEX luminotes_user_email_address_index ON luminotes_user USING btree (email_address);


--
-- Name: luminotes_user_username_index; Type: INDEX; Schema: public; Owner: luminotes; Tablespace: 
--

CREATE INDEX luminotes_user_username_index ON luminotes_user USING btree (username);


--
-- Name: note_notebook_id_startup_index; Type: INDEX; Schema: public; Owner: luminotes; Tablespace: 
--

CREATE INDEX note_notebook_id_startup_index ON note USING btree (notebook_id, startup);


--
-- Name: note_notebook_id_title_index; Type: INDEX; Schema: public; Owner: luminotes; Tablespace: 
--

CREATE INDEX note_notebook_id_title_index ON note USING btree (notebook_id, title);


--
-- Name: password_reset_email_address_index; Type: INDEX; Schema: public; Owner: luminotes; Tablespace: 
--

CREATE INDEX password_reset_email_address_index ON password_reset USING btree (email_address);


--
-- Name: search_index; Type: INDEX; Schema: public; Owner: luminotes; Tablespace: 
--

CREATE INDEX search_index ON note USING gist (search);


--
-- Name: search_update; Type: TRIGGER; Schema: public; Owner: luminotes
--

CREATE TRIGGER search_update
    BEFORE INSERT OR UPDATE ON note
    FOR EACH ROW
    EXECUTE PROCEDURE tsearch2('search', 'drop_html_tags', 'title', 'contents');


UPDATE pg_ts_cfg SET locale = 'en_US.UTF-8' WHERE ts_name = 'default';


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

