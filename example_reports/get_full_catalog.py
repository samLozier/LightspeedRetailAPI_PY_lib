'''
Retreives all product data from the items endpoint, can be modified by using the load-relations filters
the output Json file is used for some reports

This takes longer to pull than the filtered endpoints so use sparingly. I tend to only pull it 
occasionally and use it as a reference for other reports
'''

import json
import LightspeedRetailAPI_PY_lib.connection_methods.credentials as credentials
from LightspeedRetailAPI_PY_lib.connection_methods.lightspeed_conn import LightspeedStoreConn, LightspeedReports

store_credentials = credentials.lightspeed_client_credentials
devcreds = credentials.lightspeed_developer_credentials

conn = LightspeedStoreConn(store_credentials, devcreds)
conn.refresh_access()


querystring = {
    "load_relations": "all",
}
fullcatalog = LightspeedReports.get_items(conn, **querystring)
with open('../data_files/ls_fullcatalog.json', 'w+') as fullcatalogfile:
    json.dump(fullcatalog, fullcatalogfile)



