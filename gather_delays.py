import requests
import json
import pdb
import sys
import math

from qgis.core import *
from qgis.gui import *
from osgeo import ogr
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


def init_ch_layer():
    layer = QgsVectorLayer(
        "ADMGDE_GDEDAT.shp", "Indicatrix", "ogr")
    crs = layer.crs()
    crs.createFromId(2056)
    layer.setCrs(crs)
    if not layer.isValid():
        print "Failed to open the layer"

    symbols = layer.rendererV2().symbols()
    symbol = symbols[0]
    symbol.setColor(QColor.fromRgb(0, 153, 255))
    return layer


def init_features_layer():
    # create a memory layer with points
    layer = QgsVectorLayer('Point', 'points', "memory")
    layer.dataProvider().addAttributes(
        [QgsField("city",  QVariant.String), QgsField("lbl", QVariant.String)])
    layer.updateFields()

    symbols = layer.rendererV2().symbols()
    symbol = symbols[0]
    symbol.setColor(QColor.fromRgb(0, 0, 0))

    for city in results:
        long_coord = results[city]['geopos'][1]
        lat_coord = results[city]['geopos'][0]

        feature = QgsFeature()
        point = QgsPoint(long_coord, lat_coord)
        pointGeo = QgsGeometry.fromPoint(point)
        tr = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem(4326),
            QgsCoordinateReferenceSystem(2056)
        )
        pointGeo.transform(tr)
        feature.setGeometry(pointGeo)
        feat_lbl = 'Delays: ' + str(results[city]['cnt'])
        feature.setAttributes([city, feat_lbl])

        layer.dataProvider().addFeatures([feature])
        layer.updateExtents()
    return layer


if __name__ == '__main__':

    if len(sys.argv) != 2:
        print "Provide API key as parameter! Exiting..."
        exit(1)

    api_key = sys.argv[1]

    for city in cities:
        get_results_by_town(city)

    # print json.dumps(results, indent=4)

    app = QgsApplication([], True)
    QgsApplication.setPrefixPath('/usr', True)
    QgsApplication.initQgis()

    ch_layer = init_ch_layer()
    features_layer = init_features_layer()

    QgsMapLayerRegistry.instance().addMapLayer(features_layer)
    QgsMapLayerRegistry.instance().addMapLayer(ch_layer)

    palyr = QgsPalLayerSettings()
    palyr.readFromLayer(features_layer)
    palyr.enabled = True
    palyr.fieldName = 'lbl'
    palyr.placement = QgsPalLayerSettings.OverPoint
    palyr.fontSizeInMapUnits = False
    palyr.textColor = QColor(0, 0, 0)
    palyr.yOffset = -3
    palyr.setDataDefinedProperty(QgsPalLayerSettings.OffsetUnits, True, True, '1', '')
    palyr.setDataDefinedProperty(QgsPalLayerSettings.Bold, True, True, '1', '')
    palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '9', '')
    palyr.writeToLayer(features_layer)

    canvas = QgsMapCanvas()
    canvas.setCanvasColor(Qt.white)
    canvas.enableAntiAliasing(True)
    canvas.setExtent(ch_layer.extent())
    canvas.mapRenderer().setLabelingEngine(QgsPalLabeling())
    canvas.setLayerSet([
        QgsMapCanvasLayer(features_layer),
        QgsMapCanvasLayer(ch_layer)
    ])
    canvas.show()

    sys.exit(app.exec_())
