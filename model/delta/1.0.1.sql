alter table notebook add column deleted boolean default 'f';
drop view notebook_current;
create view notebook_current as select notebook.id, notebook.revision, notebook.name, notebook.trash_id, notebook.deleted from notebook where (notebook.revision in (select max(sub_notebook.revision) as max from notebook sub_notebook where (sub_notebook.id = notebook.id)));
