/* Flattened, tabular export of grants for analysis */
CREATE OR REPLACE VIEW public.view_grants_analysis_view
AS SELECT
-- grant data
g.data->>'id' AS "id",
g.data->>'title' AS "title",
g.data->>'description' AS "description",
(g.data->>'amountAwarded')::float AS "amountAwarded",
CASE WHEN g.data->>'currency' = 'GBP' THEN (g.data->>'amountAwarded')::float ELSE NULL END as "amountAwarded_GBP",
g.data->>'currency' AS "currency",
-- to_date
TO_DATE(g.data->>'awardDate','YYY-MM-DD') AS "awardDate",
g.data->>'dateModified' AS "dateModified",
(g.data->'plannedDates'->0->>'duration')::float AS "plannedDates.0.duration",
TO_DATE(LEFT(g.data->'plannedDates'->0->>'startDate',10),'YYYY-MM-DD') as "plannedDates.0.startDate",
TO_DATE(REPLACE(LEFT(g.data->'plannedDates'->0->>'endDate',10), '-06-31', '-06-30'),'YYYY-MM-DD') as "plannedDates.0.endDate",
COALESCE(
        ROUND((g.data->'plannedDates'->0->>'duration')::float)::int,
          ROUND(
        (TO_DATE(REPLACE(LEFT(g.data->'plannedDates'->0->>'endDate',10), '-06-31', '-06-30'),'YYYY-MM-DD')
     - TO_DATE(LEFT(g.data->'plannedDates'->0->>'startDate',10),'YYYY-MM-DD')) / 30.44
      )::int
    ) AS "calculated_duration_months",
g.data->'grantProgramme'->0->>'title' AS "grantProgramme.0.title",
g.data->'grantProgramme'->0->>'code' AS "grantProgramme.0.code",
g.data->'classifications'->0->>'title' AS "classifications.0.title",
g.data->>'locationScope' AS "locationScope",
g.additional_data->'codeListLookup'->>'locationScope' AS "added_locationScope",
g.data->>'regrantType' AS "regrantType",
g.additional_data->'codeListLookup'->>'regrantType' AS "added_regrantType",
g.data->'fundingType'->0->>'title' as "fundingType.title",
-- funder data
g.data->'fundingOrganization'->0->>'id' AS "fundingOrganization.0.id",
g.data->'fundingOrganization'->0->>'name' AS "fundingOrganization.0.name",
f.name AS "added_canonical_fundingOrganisation.name",
g.additional_data->>'TSGFundingOrgType' AS "added_fundingOrgType",
-- grants to individuals data
g.data->'recipientIndividual'->>'id' AS "recipientIndividuals.id",
g.data->'toIndividualsDetails'->>'primaryGrantReason' AS "toIndividualsDetails.primaryGrantReason",
g.data->'toIndividualsDetails'->>'grantPurpose' AS "toIndividualsDetails.grantPurpose",
-- grant (beneficiary) location data
g.data->'beneficiaryLocation'->0->>'name' AS "grantLocation.0.name", -- 1st record published data
g.data->'beneficiaryLocation'->0->>'geoCode' AS "grantLocation.0.geoCode", -- 1st record published data
g.data->'beneficiaryLocation' AS "benficiaryLocationArray", -- full array
jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "beneficiaryLocation").ladcd') AS "added_beneficiaryLocation.0.ladcd", -- 1st record additional data
jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "beneficiaryLocation").ladnm') AS "added_benficiaryLocation.0.ladnm", -- 1st record additional data
jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "beneficiaryLocation").rgncd') AS "added_beneficiaryLocation.0.rgncd", -- 1st record additional data
jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "beneficiaryLocation").rgnnm') AS "added_beneficiaryLocation.0.rgnm", -- 1st record additional data
jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "beneficiaryLocation").source') AS "added_beneficiaryLocation.0.source", -- 1st record additional data
-- recipient organisation data -- check future depricated fields
g.data->'recipientOrganization'->0->>'id' AS "recipientOrganization.0.id", -- 1st record published data
g.data->'recipientOrganization'->0->>'name' AS "recipientOrganization.0.name", -- 1st record published data
coalesce(g.additional_data->'recipientOrgInfos'->0->>'id',g.data->'recipientOrganization'->0->>'id') AS "calculated_canonical_recipient_id", -- derive a canonical recipient ID
coalesce(g.additional_data->'recipientOrgInfos'->0->>'name',g.data->'recipientOrganization'->0->>'name') AS "calculated_canonical_recipient_name", -- derive a canonical recipient name
jsonb_path_query_array(g.additional_data, '$.recipientOrgInfos[*].id') as "added_recipient_org_id_list", -- lists all linked org ID
g.additional_data->'recipientOrgInfos'->0->>'id' AS "added_recipientOrgInfos.0.id", -- 1st record additional data
g.additional_data->'recipientOrgInfos'->0->>'name' AS "added_recipientOrgInfos.0.regulatorName", -- 1st record additional data
g.additional_data->'recipientOrgInfos'->0->>'charityNumber' AS "added_recipientOrgInfos.0.charityNumber", -- 1st record additional data
g.additional_data->'recipientOrgInfos'->0->>'companyNumber' AS "added_recipientOrgInfos.0.companyNumber", -- 1st record additional data
g.additional_data->'recipientOrgInfos'->0->>'latestIncome' AS "added_recipientOrgInfos.0.latestIncome", -- 1st record additional data
g.additional_data->'recipientOrgInfos'->0->>'dateRegistered' AS "added_recipientOrgInfos.0.dateRegistered", -- 1st record additional data
g.additional_data->'recipientOrgInfos'->0->>'dateRemoved' AS "added_recipientOrgInfos.0.dateRemoved", -- 1st record additional data
g.additional_data->'recipientOrgInfos'->0->>'active' AS "added_recipientOrgInfos.0.regulatorActive", -- 1st record additional data
g.additional_data->'recipientOrgInfos'->0->>'source' AS "added_recipientOrgInfos.0.regulatorSource", -- 1st record additional data
g.additional_data->'recipientOrgInfos'->0->>'organisationTypePrimary' AS "added_recipientOrgInfos.0.organisationTypePrimary", -- 1st record additional data
g.additional_data->>'TSGRecipientType' AS "added_TSGRecipientType",
-- recipient org location data
g.additional_data->'recipientOrgInfos'->0->>'postalCode' AS "added_recipientOrgInfos.0.postalCode", -- 1st record additional data
COALESCE(
  jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "recipientOrganizationLocation").rgnnm')->>0,
  jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "recipientOrganizationPostcode").rgnnm')->>0
) AS "recipient_region_additional_data",
COALESCE(
  jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "recipientOrganizationLocation").ctrynm')->>0,
  jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "recipientOrganizationPostcode").ctrynm')->>0
) AS "recipient_country_additional_data",
COALESCE(
  jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "recipientOrganizationLocation").ladnm')->>0,
  jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "recipientOrganizationPostcode").ladnm')->>0
) AS "recipient_district_additional_data",
COALESCE(
  jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "recipientOrganizationLocation").ladcd')->>0,
  jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "recipientOrganizationPostcode").ladcd')->>0
) AS "recipient_district code_additional_data",
jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "recipientOrganizationLocation" && @.areatype == "ward").areaname')->>0
  AS "recipient_ward_name_additional_data",
jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "recipientOrganizationLocation" && @.areatype == "ward").areacode')->>0
  AS "recipient_ward_code_additional_data",
jsonb_path_query_array(g.additional_data, '$.locationLookup[*] ? (@.source == "recipientOrganizationPostcode")')
  AS "recipient_org_location_array_additional_data",
-- source data
g.data->>'dataSource' AS "dataSource",
g.source_data->'publisher'->>'name' AS "publisher",
g.source_data->>'license' AS "license"

FROM view_latest_grant g
LEFT JOIN (SELECT
    org_id,
    name,
    unnest(array_append(non_primary_org_ids, org_id)) AS all_ids
FROM db_funder) AS f ON g.data->'fundingOrganization'->0->>'id' = f.all_ids;
