"""Establish a set of classes to facilitate reporting with Lightspeed"""
import csv
import json
from time import sleep

import requests


class LightspeedStoreConn:
    """class for connecting to Lightspeed, other classes inherit from this"""

    def __init__(self, store_credentials_data, devcreds):
        self.access_token = ''  # need to get a new one each time using the refresh method
        self.expires_in = ''  # This can update multiple times per session
        self.token_type = store_credentials_data['token_type']
        self.scope = store_credentials_data['scope']
        self.refresh_token = store_credentials_data['refresh_token']
        self.account_id = store_credentials_data['account_id']
        self.client_id = devcreds['clientID']
        self.client_secret = devcreds['clientSec']
        self.base_url = 'https://api.lightspeedapp.com/API/Account/'

    def refresh_access(self):
        payload = {
            'refresh_token': f'{self.refresh_token}',
            'client_secret': f'{self.client_secret}',
            'client_id': f'{self.client_id}',
            'grant_type': 'refresh_token',
        }
        r = requests.request("POST",
                             'https://cloud.lightspeedapp.com/oauth/access_token.php',
                             data=payload).json()
        self.access_token = r['access_token']
        self.expires_in = r['expires_in']

    def paginate(self, raw_response, request_type):
        """controls pagination and rate limiting"""
        headers = raw_response.headers
        pagedata = raw_response.json()
        # self.expires_in = pagedata['expires_in']
        try:
            bucket_level = headers['x-ls-api-bucket-level']
            b_level, b_capacity = [(float(x)) for x in bucket_level.split('/')]
            drip_rate = float(headers['x-ls-api-drip-rate'])
            # print(f'drip rate: {drip_rate}, bucket level: {bucket_level}')
            # print(f'expires in: {self.expires_in}')
            if request_type == 'GET':
                unit_cost = 1.1
            else:
                unit_cost = 10.1
            next_level = b_level + unit_cost
            if next_level >= b_capacity:
                # print(f'sleeping: {(next_level - b_capacity) / drip_rate}')
                sleep((next_level - b_capacity) / drip_rate)
            else:
                pass
            # pagedata = raw_response.json()
            count = int(pagedata['@attributes']['count'])
            try:
                offset = int(pagedata['@attributes']['offset'])
            except:
                offset = 0
            try:
                limit = int(pagedata['@attributes']['limit'])
            except:
                limit = 0
            newlimit = offset + limit
            while newlimit < count:
                return newlimit
            else:
                return 'stop'
        except:
            if pagedata['httpCode'] == '401':
                # print(f'prev access token {self.access_token}')
                self.refresh_access()
                # print(f'after refresh access token {self.access_token}')
                sleep(1)
            elif pagedata['httpCode'] == '422':
                sleep(10)
            else:
                print(f"error: {pagedata['httpCode']}{pagedata}")
                sleep(1)


class LightspeedReports(LightspeedStoreConn):
    """Classes for accessing lightspeed reports: might need to break up"""

    def get_categories(self):
        """gets a list of categories from Lightspeed"""
        list_categories = []
        offset = 0
        headers = {
            'authorization': f'Bearer {self.access_token}'
        }

        while offset != 'stop':
            url = f'{self.base_url}{self.account_id}/Category.json?offset={offset}'
            raw_response = requests.request('GET', url, headers=headers)
            response = raw_response.json()
            catl = response['Category']
            for cat in catl:
                list_categories.append(cat)
            offset = self.paginate(raw_response, 'GET')
        return list_categories
        # TODO actually do something with this response

    def get_items(self, *kwarg, **kwargs):
        """gets a list of items from Lightspeed"""
        # print(kwargs)
        offset = 0
        itemsjson = {}
        itemsjson['item'] = []
        request_type = 'GET'
        base_endpoint = '/Item'
        headers = {
            'authorization': f'Bearer {self.access_token}'
        }
        while offset != 'stop':
            if kwarg is int:
                endpoint = f'{base_endpoint}/{kwarg}.json'
            else:
                endpoint = f'{base_endpoint}.json'

            url = f'{self.base_url}{self.account_id}{endpoint}'


            querystring = {"offset": f"{offset}"}
            querystring.update(kwargs)

            response = requests.request(request_type, url, params=querystring, headers=headers)

            while 'Item' not in response.json().keys():
                print(f"got bad response: {response.status_code}")
                offset = self.paginate(response, request_type)
                querystring = {"offset": f"{offset}"}
                print(querystring)
                querystring.update(kwargs)
                response = requests.request(request_type, url, params=querystring, headers=headers)

            json_response = response.json()
            for item in json_response['Item']:
                itemsjson['item'].append(item)
            #                 print(item)

            offset = self.paginate(response, request_type)
        return itemsjson

    def get_orders(self, **relations):  # expects a list of relations formatted like (relations=["Note"])
        """gets order information, can add relation variables"""
        list_of_orders = []
        headers = {
            'authorization': f'Bearer {self.access_token}'
        }
        if relations:
            relation_list = relations['relations']
            endpoint = f'/Order.json?load_relations={json.dumps(relation_list)}'
        else:
            endpoint = f'/Order.json'
        url = f'{self.base_url}{self.account_id}{endpoint}'
        response = requests.request('GET', url, headers=headers).json()
        order_list = response['Order']
        for order in order_list:
            list_of_orders.append(order)
        return list_of_orders


class UpdateLightspeed(LightspeedStoreConn):
    """methods for updating fields in lightspeed"""

    def update_order_notes(self, order_list):
        """NOT WORKING CURRENTLY: method for updating the note field to include the buyer and refnumber fields"""
        for order in order_list:
            order_id = order['orderID']
            note_id = order['Note']['noteID']
            note = order['Note']['note']
            refnumber = order['refNum']
            key = 'CustomFieldValues'
            if key in order.keys():
                buyer = order['CustomFieldValues']['CustomFieldValue']['value']['name']
            else:
                buyer = ''
            #  todo check for existence of notes other than replacement string
            if buyer != '' and refnumber != '':  # Check that at least one of the fields has entries

                if refnumber in note or f'PO#:{refnumber}' in note:
                    print(f'refnumber: {refnumber}\n note: {note}')
                if buyer in note:
                    print(f'buyer: {buyer}\n note: {note}')

                #  todo replace string with correct string (if statement)

                new_note = f"{buyer} - PO#:{refnumber} \n Old Note: {note}"
                print(new_note)

            else:
                continue
            # #  todo post results back to notes
            # headers = {
            #     'authorization': f'Bearer {self.access_token}'
            # }
            # endpoint = f'/Order/{order_id}.json'
            # url = f'{self.base_url}{self.account_id}{endpoint}'
            # data = {
            #     "Note": {
            #         "noteID": f"{note_id}",
            #         "note": f"{new_note}"
            #     }
            # }
            # response = requests.put(url, headers=headers, json=data)
            # if str(response) == '<Response [200]>':
            #     print(f'updated order number: {order_id}')
            #     print(f'success response: {response.text}')
            # else:
            #     print(f'error: {response.text}')

    def updateitem(self, itemlist, value_dict):
        """updates any item fields can be updated. expcts a dict with {'field':'value'} format"""
        offset = 0
        updatefile = open('updateditems.csv', 'a+', newline='')
        update = csv.writer(updatefile, delimiter=' ')
        for itemid in itemlist:
            data = value_dict
            headers = {
                'authorization': f'Bearer {self.access_token}'
            }
            endpoint = f'/Item/{itemid}.json?offset={offset}'
            url = f'{self.base_url}{self.account_id}{endpoint}'
            raw_response = requests.request('PUT', url, headers=headers, json=data)
            offset = self.paginate(raw_response, 'PUT')
            row = [f'{itemid} ::: status {raw_response.status_code}']
            update.writerow(row)
            # print(row)

        updatefile.close()

