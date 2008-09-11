CREATE TABLE download_access (
    id text NOT NULL,
    revision timestamp with time zone NOT NULL,
    item_number text,
    transaction_id text
);
ALTER TABLE ONLY download_access ADD CONSTRAINT download_access_pkey PRIMARY KEY (id);
CREATE INDEX download_access_transaction_id_index ON download_access USING btree (transaction_id);
