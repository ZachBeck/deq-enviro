# Builds a .json file used by the app. 
# Also returns lists used to update SDE and file geodatabase data.

import os
import json
import requests
import spreadsheet
from settings import fieldnames
import settings
from agrc import ags

jsonFile = os.path.join(settings.webdata, 'DEQEnviro.json')

def run():
    layers = get_dataset_info(spreadsheet.get_query_layers())
    tables = get_dataset_info(spreadsheet.get_related_tables())

    # other links
    links = spreadsheet.get_links()
    linksDict = {}
    for l in links:
        linksDict[l[fieldnames.ID]] = l

    j = {
         fieldnames.queryLayers: layers,
         fieldnames.relatedTables: tables,
         fieldnames.otherLinks: linksDict
         }
    f = open(jsonFile, 'w')
    print >> f, json.dumps(j, indent=4)
    f.close()

    return j

def get_dataset_info(spreadsheetData):
    admin = ags.AGSAdmin(settings.DEQNIGHTLY_USER, settings.DEQNIGHTLY_PASSWORD, settings.agsServer)

    # get layer indicies from map service
    jsonData = requests.get(settings.mapServiceJson).json()
    secureJsonData = requests.get('{}&token={}'.format(settings.securedServiceJson, admin.token)).json()
    layersAndTables = jsonData['layers'] + jsonData['tables'] + secureJsonData['layers']
    serviceLayers = {}
    for s in layersAndTables:
        serviceLayers[s['name']] = s['id']
    for l in spreadsheetData:
        n = l[fieldnames.sgidName].split('.')[-1]
        l[fieldnames.fields] = parse_fields(l[fieldnames.fields])
        if n in serviceLayers.keys():
            l[fieldnames.index] = serviceLayers[n]
    
    return spreadsheetData
    
def parse_fields(fieldTxt):
    fields = []
    for txt in fieldTxt.split(', '):
        splitIndex = txt.find(' (')
        fieldname = txt[:splitIndex].strip()
        alias = txt[splitIndex + 2:-1].strip()
        if fieldname is not None and alias is not None:
            fields.append([fieldname, alias])
    
    return fields

if __name__ == '__main__':
    run()
    print('done')