import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime

import requests
from django.forms.models import model_to_dict

from additional_data.models import GeoLookup

class GeoLookupSource(object):
    """Imports geographical lookups from https://github.com/drkane/geo-lookups/
    These allow for looking up from lower-level geography like Ward to a standard local authority, region, etc"""

    # Source URLS
    SOURCE_URLS = {
        'lsoa': {
            'url_lookup': "https://raw.githubusercontent.com/drkane/geo-lookups/master/lsoa_la.csv",
            'url_latlong': "https://raw.githubusercontent.com/drkane/geo-lookups/master/lsoa_latlong.csv",
            'field_areacode': 'lsoa11cd',
            'field_areaname': 'lsoa11nm',
            'field_transforms': {
                'lad20cd': 'ladcd',
                'lad20nm': 'ladnm',
            },
        },
        'msoa': {
            'url_lookup': "https://raw.githubusercontent.com/drkane/geo-lookups/master/msoa_la.csv",
            'url_latlong': "https://raw.githubusercontent.com/drkane/geo-lookups/master/msoa_latlong.csv",
            'field_areacode': 'msoa11cd',
            'field_areaname': 'msoa11hclnm',
            'field_transforms': {
                'lad20cd': 'ladcd',
                'lad20nm': 'ladnm',
            },
        },
        'ward': {
            'url_lookup': "https://raw.githubusercontent.com/drkane/geo-lookups/master/ward_all_codes.csv",
            'url_latlong': "https://raw.githubusercontent.com/drkane/geo-lookups/master/ward_latlong.csv",
            'field_areacode': 'wdcd',
            'field_areaname': 'wdnm',
        },
        'la': {
            'url_lookup': "https://raw.githubusercontent.com/drkane/geo-lookups/master/la_all_codes.csv",
            'field_areacode': 'ladcd',
            'field_areaname': 'ladnm',
            'field_transforms': {
                'lad20cd': 'ladcd',
                'lad20nm': 'ladnm',
            },
        },
    }

    def __init__(self):
        pass

    def get_lookup_data(self, areatype, a, areas):

        def clean_fields(row, a):
            for k, v in row.items():
                k = k.lower()
                if k == a.get('field_areacode'):
                    k = 'areacode'
                if k == a.get('field_areaname'):
                    k = 'areaname'
                if a.get('field_transforms', {}).get(k):
                    k = a.get('field_transforms', {}).get(k)
                yield k, v

        r = requests.get(a.get('url_lookup'), stream=True)
        area_csv = io.StringIO(r.text)
        reader = csv.DictReader(area_csv)
        for r in reader:
            data = {k: v for k, v in clean_fields(r, a)}
            data['areatype'] = areatype
            if data["areacode"] not in areas:
                areas[data['areacode']] = data

        if a.get('url_latlong'):
            r = requests.get(a.get('url_latlong'), stream=True)
            area_csv = io.StringIO(r.text)
            reader = csv.DictReader(area_csv)
            for r in reader:
                data = {k: v for k, v in clean_fields(r, a)}
                areas[data['areacode']]['latitude'] = float(data['latitude'])
                areas[data['areacode']]['longitude'] = float(data['longitude'])

        return areas

    def import_geo_lookups(self, urls=SOURCE_URLS):
        data = {}
        for areatype, a in urls.items():
            print("fetching {}".format(areatype))
            data = self.get_lookup_data(areatype, a, data)

        if GeoLookup.objects.exists():
            GeoLookup.objects.all().delete()
        GeoLookup.objects.bulk_create([GeoLookup(areacode=areacode, areatype=d['areatype'], data=d) for areacode, d in data.items()])

    def get_area_by_code(self, areacode):
        try:
            a = GeoLookup.objects.get(areacode=areacode)
            return a.data
        except GeoLookup.DoesNotExist:
            pass

    def update_additional_data(self, grant, additional_data):
        """Updates with 'locationLookup' based on available areas."""
        additional_data['locationLookup'] = []
        
        for location in grant.get("beneficiaryLocation", []):
            if location.get('geoCode'):
                a = self.get_area_by_code(location.get('geoCode'))
                if a:
                    a['source'] = 'beneficiaryLocation'
                    a['sourceCode'] = location.get('geoCode')
                    additional_data['locationLookup'].append(a)

        if additional_data['locationLookup']:
            # if we've found data then return
            return
        
        for recipient in grant.get("recipientOrganization", []):
            for location in recipient.get('location', []):
                if location.get('geoCode'):
                    a = self.get_area_by_code(location.get('geoCode'))
                    if a:
                        a['source'] = 'recipientOrganizationLocation'
                        a['sourceCode'] = location.get('geoCode')
                        additional_data['locationLookup'].append(a)

        if additional_data['locationLookup']:
            # if we've found data then return
            return

        lsoa = additional_data.get("recipientOrganizationLocation", {}).get('lsoa11')
        if lsoa:
            a = self.get_area_by_code(lsoa)
            if a:
                a['source'] = 'recipientOrganizationPostcode'
                a['sourceCode'] = lsoa
                additional_data['locationLookup'].append(a)
