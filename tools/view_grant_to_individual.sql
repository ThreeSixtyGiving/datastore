CREATE OR REPLACE VIEW view_grant_to_individual AS

WITH raw_df AS(
   SELECT db_grant.id,
		  db_grant.grant_id,
		  db_grant.data,
		  db_grant.additional_data
   FROM   db_grant
   JOIN   db_sourcefile_latest
   ON     db_grant.source_file_id = db_sourcefile_latest.sourcefile_id
   JOIN   db_latest
   ON     db_sourcefile_latest.latest_id = db_latest.id
   WHERE  db_latest.series = 'CURRENT'::text
   AND    jsonb_extract_path_text(db_grant.data, 'recipientIndividual') IS NOT NULL
),

flatten_df AS(
   SELECT r.id as uuid,
		  r.grant_id as grantId,
		  r.data ->> 'title' AS grantTitle,
		  r.data ->> 'description' AS description,
		  r.data ->> 'currency' AS currency,
		  (r.data ->> 'amountAwarded')::float AS amountAwarded,
		  to_date(r.data ->> 'awardDate','YYYY-MM-DD') AS awardDate,
		  r.data -> 'grantProgramme' -> 0 ->> 'title' AS grantProgrammeTitle,
                r.data -> 'beneficiaryLocation' -> 0 ->> 'name' AS beneficiaryLocationName1,
		  r.data -> 'beneficiaryLocation' -> 0 ->> 'geoCode' AS beneficiaryLocationGeocode1,
		  r.data -> 'beneficiaryLocation' -> 0 ->> 'geoCodeType' AS beneficiaryLocationGeocodeType1,
		  r.data -> 'beneficiaryLocation' -> 1 ->> 'name' AS beneficiaryLocationName2,
		  r.data -> 'beneficiaryLocation' -> 1 ->> 'geoCode' AS beneficiaryLocationGeocode2,
		  r.data -> 'beneficiaryLocation' -> 1 ->> 'geoCodeType' AS beneficiaryLocationGeocodeType2,
		  r.data -> 'fundingOrganization' -> 0 ->> 'id' AS fundingOrganizationId,
		  r.data -> 'fundingOrganization' -> 0 ->> 'name' AS fundingOrganizationName,
		  r.additional_data -> 'codeListLookup' -> 'toIndividualsDetails' -> 'grantPurpose' ->> 0 AS grantPurpose1,
		  r.additional_data -> 'codeListLookup' -> 'toIndividualsDetails' -> 'grantPurpose' ->> 1 AS grantPurpose2,
		  r.additional_data -> 'codeListLookup' -> 'toIndividualsDetails' -> 'grantPurpose' ->> 2 AS grantPurpose3,
		  r.additional_data -> 'codeListLookup' -> 'toIndividualsDetails' ->> 'primaryGrantReason' AS primaryGrantReason,
		  r.additional_data -> 'codeListLookup' -> 'toIndividualsDetails' ->> 'secondaryGrantReason' AS secondaryGrantReason,
		  r.data ->> 'Ward' AS wardName,
		  r.additional_data ->> 'recipientRegionName' AS recipientregionname,
		  r.additional_data ->> 'recipientDistrictName' AS recipientdistrictname,
		  r.additional_data ->> 'recipientDistrictGeoCode' AS recipientdistrictgeocode,
	      COALESCE(r.additional_data ->> 'recipientDistrictGeoCode', r.data -> 'beneficiaryLocation' -> 0 ->> 'geoCodeType') AS cleanDistrictCode

	FROM raw_df AS r
),

grant_df as (
       SELECT uuid,
              grantId,
              grantTitle,
              grantProgrammeTitle,
              description,
              currency,
              fundingOrganizationId,
              fundingOrganizationName,
              amountAwarded,
			  awardDate,
              grantPurpose1,
              grantPurpose2,
              grantPurpose3,
              primaryGrantReason,
              SecondaryGrantReason,
              CASE
                     WHEN amountAwarded <= 50 THEN '1. Up to £50'
                     WHEN amountAwarded <= 100 THEN '2. £51-£100'
                     WHEN amountAwarded <= 200 THEN '3. £101-£200'
                     WHEN amountAwarded <= 500 THEN '4. £201-£500'
                     WHEN amountAwarded <= 1000 THEN '5. £501-£1,000'
                     WHEN amountAwarded <= 2000 THEN '6. £1,001-£2,000'
                     WHEN amountAwarded <= 5000 THEN '7. £2,001-£5,000'
                     WHEN amountAwarded <= 10000 THEN '8. £5,001-£10,000'
                     WHEN amountAwarded > 10000 THEN '9. Over £10,000'
              END AS amountAwardedGroup,
              CASE
                     WHEN beneficiaryLocationGeocode1 LIKE ANY (array['E05%','S13%','W05%','N08%']) THEN 1
                     ELSE 0
              END AS containWdCode,
              CASE
                     WHEN beneficiaryLocationGeocode1 LIKE ANY (array['E05%','S13%','W05%','N08%'])THEN beneficiaryLocationGeocode1
                     ELSE NULL
              END AS wdCode,
              CASE
                     WHEN beneficiaryLocationGeocode1 LIKE ANY (array['E05%','S13%','W05%','N08%']) THEN beneficiaryLocationName1
                     WHEN wardName IS NOT NULL THEN wardName
                     ELSE NULL
              END AS wdName,
              CASE
                     WHEN cleanDistrictCode LIKE ANY (array['E06%','E07%','E08%','E09%','S12%','W06%','N09%']) THEN 1
                     ELSE 0
              END AS containLaCode,
              CASE
                     WHEN cleanDistrictCode LIKE ANY (array['E06%','E07%','E08%','E09%','S12%','W06%','N09%']) THEN cleanDistrictCode
                     ELSE NULL
              END AS laCode
	FROM flatten_df
)


SELECT g.*,
	a.wd23nm,
	a.uk_imd_e_score,
	a.original_decile,
	a.e_expanded_decile,
	a.uk_imd_e_rank,
	a.uk_imd_e_pop_decile,
	a.uk_imd_e_pop_quintile,
	a.total_population
FROM grant_df AS g
LEFT JOIN additional_data_imdwardlookup AS a
ON g.wdCode = a.wd23cd
