import requests as requests
import os
import sys as sys
from pathlib import Path
import logging as log
from pprint import pformat
from operator import itemgetter

# noinspection PyArgumentList
log.basicConfig(level=log.INFO, format='%(message)s',
                handlers=[log.FileHandler('wi_creation_logs.log', mode='a'),
                          log.StreamHandler(sys.stdout)])


class AdoWiManager:
    # runtime cache
    attch_cache = {}

    def __init__(self, ado_config):
        # instantiating ado api network session
        self.api_session = requests.session()
        self.api_session.auth = itemgetter('user id', 'pat')(ado_config)
        self.org, self.proj, self.api_version = itemgetter('org', 'proj', 'api version')(ado_config)
        self.wit_base_url = f'https://dev.azure.com/{self.org}/{self.proj}/_apis/wit'
        self.wit_org_base_url = f'https://dev.azure.com/{self.org}/_apis/wit'
        self.wi_base_url = f'{self.wit_base_url}/workitems'
        self.wi_headers = ado_config['wi headers']
        self.attch_def_name = ado_config['attch default name']
        self.wi_fields_refs = self.get_wi_fields_refs()
        self.wi_rels_refs = self.get_wi_rels_refs()

    def get_api_response(self, operation, url, headers=None, body=None, byte_data=None):
        """ Makes network calls and catches errors """
        try:
            return operation(url, headers=headers, json=body, data=byte_data)
        except requests.exceptions.RequestException as err:
            print(f'Network error: {err}')

    def _log_response_and_get_value(self, response, capture_key='', log_value=True, operation=''):
        """ Returns the value for required key from api response and handles logging """
        invalid_response = '-1'
        response_ok = [200, 201]
        if response.status_code in response_ok:
            value = response.json()[capture_key] if capture_key else 'done'
            if log_value:
                log.info(f'{operation} : {value}')
            return value
        else:
            log.info(f'{operation} failed with response: {response.json()}')
            return invalid_response

    def get_wi_rels_refs(self):
        """ Returns a dict of {name:reference name} for all WI RELs in ADO """
        rels_url = f'{self.wit_org_base_url}/workitemrelationtypes?{self.api_version}'
        wi_rels = self._log_response_and_get_value(response=self.get_api_response(self.api_session.get, rels_url),
                                                   capture_key='value', log_value=False)
        rels_refs = {wi_rel['name']: wi_rel['referenceName'] for wi_rel in wi_rels}
        return rels_refs

    def get_wi_fields_refs(self):
        """ Returns a list of reference names for all readwrite WI fields in ADO """
        fields_url = f'{self.wit_base_url}/fields?{self.api_version}'
        wi_fields = self._log_response_and_get_value(response=self.get_api_response(self.api_session.get, fields_url),
                                                     capture_key='value', log_value=False)
        fields_refs = [wi_field['referenceName']
                       for wi_field in wi_fields if wi_field['readOnly'] == False]
        return fields_refs

    def upload_attachment_and_get_url(self, attachment_path):
        """ Uploads attachment file to ADO and returns the url """
        if not attachment_path.exists():
            return None
        _, attachment_name = os.path.split(attachment_path)
        if self.attch_def_name:
            attachment_name = self.attch_def_name
        attachment_endpoint = f'{self.wit_base_url}/attachments?fileName={attachment_name}' \
                              f'&uploadType=Simple&{self.api_version}'
        stream_headers = {'Content-Type': 'application/octet-stream'}
        with open(attachment_path, 'rb') as attachment:
            return self._log_response_and_get_value(operation='Url of Uploaded Attachment',
                                                    response=self.get_api_response(self.api_session.post,
                                                                                   attachment_endpoint,
                                                                                   headers=stream_headers,
                                                                                   byte_data=attachment),
                                                    capture_key='url')

    def _validate_and_cache_url_of_uploaded_attachment(self, wi_rel_url):
        """ Validates if wi_rel_url is a path, uploads attachment if filepath is not found in runtime cache
        and fetches url if a local path is provided instead of url for wi_rel_url """
        if not wi_rel_url.startswith('http'):
            wi_attch_path = Path(wi_rel_url)
            if wi_attch_path not in AdoWiManager.attch_cache.keys():
                wi_rel_url = self.upload_attachment_and_get_url(wi_attch_path)
                if wi_rel_url:
                    AdoWiManager.attch_cache[wi_attch_path] = wi_rel_url
                else:
                    log.info(f'Attachment file {wi_attch_path} doesnt exist')
            else:
                wi_rel_url = AdoWiManager.attch_cache[wi_attch_path]
        else:
            log.info('Invalid Filepath provided for wi_rel_url')
        return wi_rel_url

    def get_relation_request_body(self, wi_rel_type, wi_rel_url, wi_rel_comment=''):
        """ Receives REL type, url/filepath, optional comment and returns request body for adding relation """
        if wi_rel_type == 'AttachedFile':
            wi_rel_url = self._validate_and_cache_url_of_uploaded_attachment(wi_rel_url)
            if not wi_rel_url:
                return None
        return {
            'op': 'add',
            'path': '/relations/-',
            'value': {
                'rel': f'{wi_rel_type}',
                'url': f'{wi_rel_url}',
                'attributes': {
                    'comment': f'{wi_rel_comment}'
                }
            }
        }

    def get_wi_ref_map(self, wi_map):
        """ Receives WI map and returns new map with all display_field names replaced with reference_field names """
        wi_ref_map = {}
        for display_field, val in wi_map.items():
            ref_field = next(
                (ref_field for ref_field in self.wi_fields_refs if
                 ref_field.split('.')[-1].startswith(display_field.replace(" ", ""))), None)
            wi_ref_map[ref_field if ref_field else display_field] = val
        return wi_ref_map

    def get_wi_ref_rels(self, wi_rels):
        """ Receives WI RELS list and returns new list with all REL type names replaced with reference names """
        wi_ref_rels = []
        for wi_rel in wi_rels:
            ref_rel_field = next(
                (ref_rel for rel, ref_rel in self.wi_rels_refs.items() if rel == wi_rel['wi_rel_type']), None)
            if ref_rel_field:
                wi_rel['wi_rel_type'] = ref_rel_field
            wi_ref_rels.append(wi_rel)
        return wi_ref_rels

    def get_wi_response(self, wi_id):
        """ Receives WI id and returns dictionary of all fields with a value(UI fields with values + System fields) 
        from the get response of ADO WI """
        get_wi_url = f'{self.wi_base_url}/{wi_id}?{self.api_version}'
        return self._log_response_and_get_value(response=self.get_api_response(self.api_session.get, get_wi_url),
                                                capture_key='fields', log_value=False)

    def create_wi(self, wi_map, wi_rels, wi_type):
        """ Receives WI type, map of fields and values, list of RELs with fields and values and create a WI """
        final_wi_rels = [self.get_relation_request_body(**wi_rel) for wi_rel in wi_rels]
        if None in final_wi_rels:
            log.info('Aborting WI creation as mandatory attachment file is missing')
        else:
            create_wi_url = f'{self.wi_base_url}/${wi_type}?{self.api_version}'
            payload = [{'op': 'add', 'path': f'/fields/{field}', 'from': 'null', 'value': f'{val}'}
                       for field, val in wi_map.items()]
            payload.extend(final_wi_rels)
            log.info(f'WI map:\n{pformat(wi_map)}')
            log.info(f'WI relations:\n{pformat(final_wi_rels)}')
            return self._log_response_and_get_value(operation=f'Created {wi_type}',
                                                    response=self.get_api_response(self.api_session.patch,
                                                                                   create_wi_url,
                                                                                   headers=self.wi_headers,
                                                                                   body=payload),
                                                    capture_key='id')

    def create_wi_batch(self, wis_maps, wis_rels, wi_type):
        for wi_map, wi_rels in zip(wis_maps, wis_rels):
            self.create_wi(wi_map, wi_rels, wi_type)
