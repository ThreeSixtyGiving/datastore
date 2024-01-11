# 360 Giving Organisation & Grants API

## Motivation

This API is intended to make live data more accessible to funders, publishers and researchers who are interested in the organisations involved in grant giving.

While the data can already be accessed by downloading daily packages, or Colab scripts by advanced users, this API will make it easier to access smaller sets of up-to-date information for use by analysis or other reporting or automation tools.

Note that this API is not intended to replicate the generic search functionality of GrantNav.


## Status

This API is currently under development, and may be subject to significant change before before stability is reached. We welcome suggestions for improvements at this time.

## Data Exposed

This API exposes some aggregate information about Organisations in our database who have published, made or received grants, along with detail of the grants they have published/made/received. Organisations can be discovered by their Org ID and data is presented in JSON format.

Org ID is a standard for Organisation identifiers across all sectors and locations, to learn more see <https://org-id.guide/about>.

## Endpoints & Examples

### Endpoints Overview

* `/api/experimental/org/`: Paginated List of all known Organisations
* `/api/experimental/org/<org-id>/`: Detail about a specific Organisation, specified by Org ID.
* `/api/experimental/org/<org-id>/grants_made`: Paginated List of Grants made by this Org
* `/api/experimental/org/<org-id>/grants_received`: Paginated List of Grants Received by this Org


### Organisation Detail Example

```GET /api/experimental/org/GB-SC-SC012710```

```json
{
    "self": "/api/experimental/org/GB-SC-SC012710",
    "org_id": "GB-SC-SC012710",
    "name": "R S Macdonald Charitable Trust",
    "grants_made": "/api/experimental/org/GB-SC-SC012710/grants_made",
    "grants_received": "/api/experimental/org/GB-SC-SC012710/grants_received",
    "funder": {
        "org_id": "GB-SC-SC012710",
        "name": "R S Macdonald Charitable Trust",
        "aggregate": {
            "grants": 723,
            "currencies": {
                "GBP": {
                    "avg": 27874.103734439836,
                    "max": 150000,
                    "min": 1000,
                    "total": 20152977,
                    "grants": 723
                }
            }
        }
    },
    "recipient": null,
    "publisher": {
        "data": {
            "logo": "https://www.threesixtygiving.org/wp-content/uploads/Midnight_on_Blue.jpg",
            "name": "R S Macdonald Charitable Trust",
            "org_id": "GB-SC-SC012710",
            "prefix": "360G-RSMCT",
            "website": "http://www.rsmacdonald.com/",
            "last_published": "2023-06-29"
        },
        "quality": {
            "hasGrantDuration": 100,
            "has50pcExternalOrgId": 100,
            "hasGrantClassification": 0,
            "hasGrantProgrammeTitle": 0,
            "hasRecipientOrgLocations": 100,
            "hasBeneficiaryLocationName": 0,
            "hasBeneficiaryLocationGeoCode": 0,
            "hasRecipientOrgCompanyOrCharityNumber": 100
        }
    }
}
```

### Grants Made/Received Example

```
```

```json
{
  "count": 723,
  "next": "/api/experimental/org/GB-SC-SC012710/grants_made?limit=60&offset=60",
  "previous": null,
  "results": [
    {
      "self": "/api/experimental/grant/360G-RSMCT-0064K000001fDoq",
      "publisher": {
        "org_id": "GB-SC-SC012710",
        "self": "/api/experimental/org/GB-SC-SC012710"
      },
      "recipients": [
        {
          "org_id": "GB-SC-SC031921",
          "self": "/api/experimental/org/GB-SC-SC031921"
        }
      ],
      "funders": [
        {
          "org_id": "GB-SC-SC012710",
          "self": "/api/experimental/org/GB-SC-SC012710"
        }
      ],
      "grant_id": "360G-RSMCT-0064K000001fDoq",
      "data": {
        "id": "360G-RSMCT-0064K000001fDoq",
        "title": "DASH Club: After School",
        "currency": "GBP",
        "awardDate": "2020-10-05T00:00:00+00:00",
        "dataSource": "https://www.rsmacdonald.com/reports",
        "description": "Seeking a contribution towards overall running costs for the DASH afterschool club for young people (aged 11 -18) to continue to support those with complex disabilities including neurological conditions. ",
        "dateModified": "2021-04-01T00:00:00+00:00",
        "amountAwarded": 15000,
        "fundingOrganization": [
          {
            "id": "GB-SC-SC012710",
            "name": "R S Macdonald Charitable Trust"
          }
        ],
        "recipientOrganization": [
          {
            "id": "GB-SC-SC031921",
            "url": "https://www.dashclubglasgow.org.uk",
            "name": "DASH Club, The",
            "postalCode": "G22 5LQ",
            "charityNumber": "SC031921",
            "companyNumber": "SC387578",
            "addressLocality": "Glasgow"
          }
        ]
      }
    }
  ]
}
```

## Potential Further Improvements

Some possible additions or improvements:

### Organisations

 * Further breakdown of aggregate data about Funders / Recipients, e.g.:
   * Total number of grants made/received per year (or other time period)
   * Total value of grants made/received per year per currency
 * Further Quality info about Publishers
 * Coalesce related Organisations to show all grants/aggregate data for multiple related organisations together.
 * Include any other info shown in GrantNav
 * Lookup more Organisation info, e.g. alternative names, links to e.g. website or charity commission page
 
### Grants

 * Beneficiary location lookups, e.g. lookup higher-level regions and codes from lower-level codes.
 * Extra Organisation data alongside each grant.
