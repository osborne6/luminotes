CREATE FUNCTION friendly_id(text) RETURNS text
    AS $_$select regexp_replace( regexp_replace( lower( $1 ), '\\s+', '-', 'g' ), '[^a-zA-Z0-9\\-]', '', 'g' );$_$
    LANGUAGE sql IMMUTABLE;
CREATE INDEX notebook_friendly_id_index ON notebook USING btree (friendly_id(name));
