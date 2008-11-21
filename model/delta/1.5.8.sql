CREATE OR REPLACE FUNCTION friendly_id(text) RETURNS text
    AS $_$select trim( both '-' from
      regexp_replace(
        regexp_replace(
          regexp_replace(
            lower( $1 ),
            '&[a-zA-Z]+;|&#\\d+;', ' ', 'g'
          ),
          '\\s+', '-', 'g'
        ),
        '[^a-zA-Z0-9\\-]', '', 'g'
      )
    );$_$
    LANGUAGE sql IMMUTABLE;
reindex index notebook_friendly_id_index;
