# -*- coding: utf-8 -*-
""" Google Contact Importer module """

from .base import BaseProvider
from lxml import etree
from urllib.parse import urlencode
import requests
import json

AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://accounts.google.com/o/oauth2/token"
PERM_SCOPE = "https://www.googleapis.com/auth/contacts.readonly"
CONTACTS_URL = "https://www.google.com/m8/feeds/contacts/default/full?max-results=2000"


class GoogleContactImporter(BaseProvider):

    def __init__(self, client_id, client_secret, redirect_url):
        super(GoogleContactImporter, self).__init__(client_id, client_secret, redirect_url)
        self.auth_url = AUTH_URL
        self.token_url = TOKEN_URL

    def request_authorization(self):
        auth_params = {
            "response_type": "code",
            "scope": PERM_SCOPE,
            "redirect_uri": self.redirect_url,
            "client_id": self.client_id
        }

        return "%s?%s" % (self.auth_url, urlencode(auth_params))

    def request_access_token(self, code):
        access_token_params = {
            "code" : code,
            "client_id" : self.client_id,
            "client_secret" : self.client_secret,
            "redirect_uri" : self.redirect_url,
            "grant_type": "authorization_code",
        }

        content_length = len(urlencode(access_token_params))
        access_token_params['content-length'] = str(content_length)

        response = requests.post(self.token_url, data=access_token_params)
        data = json.loads(response.text)
        return data.get('access_token')

    def import_contacts(self, access_token):
        authorization_header = {
            "Authorization": "OAuth %s" % access_token, 
            "GData-Version": "3.0"
        }
        response = requests.get(CONTACTS_URL, headers=authorization_header)
        return self.parse_contacts(response.text)

    def parse_contacts(self, contacts_xml=None):
        parser = etree.XMLParser(ns_clean=True, recover=True, encoding="utf-8")
        root = etree.fromstring(contacts_xml.encode("utf-8"), parser)
        elms = root.findall("{http://www.w3.org/2005/Atom}entry")
        contacts = []
        
        for elm in elms:
            contact = {
                'id' : None,
                'full_name' : None,
                'email_addresses' : [],
                'phone_numbers' : []
            }
            children = elm.getchildren()
            for child in children:
                if child.tag == "{http://schemas.google.com/g/2005}name":
                   name_elms = child.getchildren()
                   for name_elm in name_elms:
                       if name_elm.tag == "{http://schemas.google.com/g/2005}fullName":
                           contact['full_name'] = name_elm.text
                elif child.tag == "{http://schemas.google.com/g/2005}email":
                    contact['email_addresses'].append(
                        {
                            'email_address': child.attrib.get('address'),
                            'type': 'TODO'
                        }
                    )
                elif child.tag == "{http://schemas.google.com/g/2005}phoneNumber":
                    type = child.attrib.get('rel')
                    if type:
                        type = type.replace('http://schemas.google.com/g/2005#', '')

                    phone_number = child.attrib.get('uri')
                    if phone_number:
                        phone_number = phone_number.replace('tel:', '')
                    contact['phone_numbers'].append(
                        {
                            'phone_number': phone_number,
                            'type': type
                        }
                    )
                elif child.tag == "{http://schemas.google.com/g/2005}id":
                    contact['id'] = child.text


            if contact.get('full_name'):
                contacts.append(contact)

        return contacts
