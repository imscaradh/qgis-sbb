import requests
import json
import pdb
import sys

from qgis.core import *
from qgis.gui import *
from PyQt4 import *
from PyQt4 import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *

req_url = 'https://data.sbb.ch/api/records/1.0/search/'

cities = {
    'Thun',
    'Bern',
    'Biel/Bienne',
    'Langenthal',
    'Langnau',
}

api_key = ''
results = {}


def get_results_by_town(town_name):
    params = {
        'apikey': api_key,
        'dataset': 'ist-daten-sbb',
        'rows': 1000,
        'q': 'haltestellen_name:"' + town_name + '"',
    }

    response = requests.get(req_url, params)
    data = response.json()

    records = data['records']

    for record in records:
        fields = record['fields']

        dict_key = fields['haltestellen_name']
        has_delay = fields['abfahrtsverspatung'] or fields['faellt_aus_tf']

        # Ugly workaround since the request fulltext query searcher performs
        # wildcard searches
        if dict_key not in cities:
            return

        if not results.get(dict_key):
            results[dict_key] = {}
            results[dict_key]['cnt'] = 0
            results[dict_key]['geopos'] = fields['geopos']

        elif has_delay:
            results[dict_key]['cnt'] += 1


if __name__ == '__main__':

    if len(sys.argv) != 2:
        print "Provide API key as parameter! Exiting..."
        exit(1)

    api_key = sys.argv[1]

    # for city in cities:
    #     get_results_by_town(city)

    # print json.dumps(results, indent=4)

    app = QgsApplication([], True)
    QgsApplication.setPrefixPath('/usr', True)
    QgsApplication.initQgis()

    canvas = QgsMapCanvas()
    canvas.setCanvasColor(Qt.white)
    canvas.enableAntiAliasing(True)
    canvas.show()

    layer = QgsVectorLayer(
        "ADMGDE_GDEDAT.shp", "Indicatrix", "ogr")
    if not layer.isValid():
        print "Failed to open the layer"

    QgsMapLayerRegistry.instance().addMapLayer(layer)
    canvas.setExtent(layer.extent())
    canvas.setLayerSet([QgsMapCanvasLayer(layer)])

    app.exec_()
    QgsApplication.exitQgis()
