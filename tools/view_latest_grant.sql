/* Useful view for latest grants */
CREATE OR REPLACE VIEW public.view_latest_grant
AS SELECT db_grant.id,
    db_grant.grant_id,
    db_grant.data,
    db_grant.source_file_id,
    db_grant.getter_run_id,
    db_grant.publisher_id,
    db_grant.additional_data,
    db_sourcefile.data as source_data
   FROM db_grant
     JOIN db_sourcefile_latest ON db_grant.source_file_id = db_sourcefile_latest.sourcefile_id
     JOIN db_latest ON db_sourcefile_latest.latest_id = db_latest.id
     JOIN db_sourcefile on db_grant.source_file_id = db_sourcefile.id
  WHERE db_latest.series = 'CURRENT'::text;
