--
-- PostgreSQL database dump
--

SET client_encoding = 'UTF8';
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

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
    SELECT DISTINCT ON (luminotes_user.id) luminotes_user.id, luminotes_user.revision, luminotes_user.username, luminotes_user.salt, luminotes_user.password_hash, luminotes_user.email_address, luminotes_user.storage_bytes, luminotes_user.rate_plan FROM luminotes_user ORDER BY luminotes_user.id, luminotes_user.revision DESC;


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
    rank numeric
);


ALTER TABLE public.note OWNER TO luminotes;

--
-- Name: note_current; Type: VIEW; Schema: public; Owner: luminotes
--

CREATE VIEW note_current AS
    SELECT DISTINCT ON (note.id) note.id, note.revision, note.title, note.contents, note.notebook_id, note.startup, note.deleted_from_id, note.rank FROM note ORDER BY note.id, note.revision DESC;


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
    SELECT DISTINCT ON (notebook.id) notebook.id, notebook.revision, notebook.name, notebook.trash_id FROM notebook ORDER BY notebook.id, notebook.revision DESC;


ALTER TABLE public.notebook_current OWNER TO luminotes;

--
-- Name: password_reset; Type: TABLE; Schema: public; Owner: luminotes; Tablespace: 
--

CREATE TABLE password_reset (
    id text NOT NULL,
    email_address text NOT NULL,
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
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

