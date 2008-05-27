create table luminotes_group ( id text not null, revision timestamp with time zone not null, name text );
create index luminotes_group_pkey on luminotes_group using btree ( id, revision );
create view
  luminotes_group_current as
  select
    luminotes_group.id, luminotes_group.revision, luminotes_group.name
  from
    luminotes_group
  where
    ( luminotes_group.revision in (
      select
        max( sub_group.revision ) as max
      from
        luminotes_group sub_group
      where
        sub_group.id = luminotes_group.id
    ) );
create table user_group ( user_id text not null, group_id text not null, admin boolean default false );
