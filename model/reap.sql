-- Delete old demo users.
delete from
  luminotes_user
where
  username is null
  and
    luminotes_user.revision < now() - interval '1 day';

-- Delete permissions for users who no longer exist.
delete from
  user_notebook
where
  user_id not in (
    select id from luminotes_user_current
  );

-- Delete trash notebooks of forever-deleted notebooks, and all past revisions of them.
delete from
  notebook
where
  notebook.id in (
    select
      trash_id
    from
      notebook_current
    where
      id not in
        ( select notebook_id from user_notebook )
    and
      notebook_current.revision < now() - interval '1 day'
  );

-- Delete forever-deleted notebooks, and all past revisions of them.
delete from
  notebook
where
  notebook.id in (
    select
      id
    from
      notebook_current
    where
      id not in
        ( select notebook_id from user_notebook )
    and
      notebook_current.revision < now() - interval '1 day'
  );

-- Delete unused next ids, forever-deleted notes, and notes whose notebooks no longer exist.
-- Also delete all past revisions of these notes.
delete from
  note
where
  note.id in (
    select
      id
    from
      note_current
    where (
      notebook_id is null or notebook_id not in
        ( select notebook_id from notebook_current )
    )
    and
      note_current.revision < now() - interval '1 day'
  );

delete from
  note_current
where (
  notebook_id is null or notebook_id not in
    ( select notebook_id from notebook_current )
)
and
  note_current.revision < now() - interval '1 day';

-- Delete unused file next ids and files whose notebooks or notes no longer exist.
delete from
  file
where (
  notebook_id is null or notebook_id not in
    ( select notebook_id from notebook_current )
  or note_id not in
    ( select note_id from note_current )
)
and
  file.revision < now() - interval '1 day';

-- Delete old notebook revisions.
delete from
  notebook
where
  revision not in (
    SELECT
      max( sub_notebook.revision ) as max
    from
      notebook sub_notebook
    where
      sub_notebook.id = notebook.id
  )
  and
    notebook.revision < now() - interval '1 week';

-- Delete old group revisions.
delete from
  luminotes_group
where
  revision not in (
    SELECT
      max( sub_group.revision ) as max
    from
      luminotes_group sub_group
    where
      sub_group.id = luminotes_group.id
  )
  and
    luminotes_group.revision < now() - interval '1 week';

-- Delete old user revisions.
delete from
  luminotes_user
where
  revision not in (
    SELECT
      max( sub_luminotes_user.revision ) as max
    from
      luminotes_user sub_luminotes_user
    where
      sub_luminotes_user.id = luminotes_user.id
  )
  and
    luminotes_user.revision < now() - interval '1 week';

-- Delete permissions for notebooks that no longer exist.
delete from
  user_notebook
where
  notebook_id not in (
    select id from notebook_current
  );

-- Delete permissions for users that no longer exist.
delete from
  user_notebook
where
  user_id not in (
    select id from luminotes_user_current
  );

-- Delete memberships to groups that no longer exist.
delete from
  user_group
where
  group_id not in (
    select id from luminotes_group_current
  );

-- Delete memberships of users that no longer exist.
delete from
  user_group
where
  user_id not in (
    select id from luminotes_user_current
  );

vacuum analyze;
