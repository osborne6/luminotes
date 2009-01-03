DROP VIEW notebook_current;
CREATE VIEW notebook_current AS
    SELECT id, revision, name, trash_id, deleted, user_id FROM notebook WHERE (notebook.revision IN (SELECT max(sub_notebook.revision) AS max FROM notebook sub_notebook WHERE (sub_notebook.id = notebook.id))) and notebook.name is not null;
