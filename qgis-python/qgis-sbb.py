# coding: utf8
import requests
import json
import sys

from qgis.core import *
from qgis.gui import *
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
    'Interlaken Ost',
    'Basel SBB',
    'Luzern',
    'Chur',
    'Brugg AG',
}

api_key = ''
results = {}
lbl_name = 'lbl'


def get_results_by_town(town_name):
    """Request JSON from SBB-API by bhf name"""
    params = {
        'apikey': api_key,
        'dataset': 'ist-daten-sbb',
        'rows': 1000,
        'q': 'haltestellen_name:' + town_name,
    }

    response = requests.get(req_url, params)
    data = response.json()

    records = data['records']

    # Rearrange JSON file for further processing
    for record in records:
        fields = record['fields']

        dict_key = fields['haltestellen_name']

        # Ugly workaround since the request fulltext query searcher performs
        # wildcard searches
        if dict_key not in cities:
            return

        if not results.get(dict_key):
            results[dict_key] = {}
            results[dict_key]['delays'] = 0
            results[dict_key]['outages'] = 0
            results[dict_key]['geopos'] = fields['geopos']

        elif fields['abfahrtsverspatung'] == 'true':
            results[dict_key]['delays'] += 1
        elif fields['faellt_aus_tf'] == 'true':
            results[dict_key]['outages'] += 1


def init_ch_layer():
    """Initialize CH-Canton borders from shapefile"""
    # Shapefile from
    # http://www.arcgis.com/home/item.html?id=a5067fb3b0b74b188d7b650fa5c64b39
    layer = QgsVectorLayer("Kantone.shp", "Kantone", "ogr")
    crs = layer.crs()
    crs.createFromId(2056)
    layer.setCrs(crs)
    if not layer.isValid():
        print "Failed to open the layer"

    symbols = layer.rendererV2().symbols()
    symbol = symbols[0]
    symbol.setColor(QColor.fromRgb(211, 255, 211))

    return layer


def init_features_layer():
    """Create layer with outages and delays as features"""
    # create a memory layer with points
    layer = QgsVectorLayer('Point', 'points', "memory")
    layer.dataProvider().addAttributes([QgsField(lbl_name, QVariant.String)])
    layer.updateFields()

    symbols = layer.rendererV2().symbols()
    symbol = symbols[0]
    symbol.setColor(QColor.fromRgb(0, 0, 0))

    # One feature contains the geopos, no. of outages and delays
    for city in results:
        long_coord = results[city]['geopos'][1]
        lat_coord = results[city]['geopos'][0]

        feature = QgsFeature()
        point = QgsPoint(long_coord, lat_coord)
        pointGeo = QgsGeometry.fromPoint(point)
        tr = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem(4326),
            QgsCoordinateReferenceSystem(21781)
        )
        pointGeo.transform(tr)
        feature.setGeometry(pointGeo)
        feat_lbl = city + '\n\nDelays: ' + \
            str(results[city]['delays']) + '\nOutages:' + \
            str(results[city]['outages'])
        feature.setAttributes([feat_lbl])

        layer.dataProvider().addFeatures([feature])
        layer.updateExtents()
    return layer


def configure_labels(layer, field_name):
    """Setup labels for features"""
    palyr = QgsPalLayerSettings()
    palyr.readFromLayer(layer)
    palyr.enabled = True
    palyr.fieldName = field_name
    palyr.placement = QgsPalLayerSettings.OverPoint
    palyr.fontSizeInMapUnits = False
    palyr.textColor = QColor(0, 0, 0)
    palyr.yOffset = -0
    palyr.setDataDefinedProperty(
        QgsPalLayerSettings.OffsetUnits, True, True, '1', '')
    palyr.setDataDefinedProperty(QgsPalLayerSettings.Bold, True, True, '1', '')
    palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '9', '')
    palyr.writeToLayer(features_layer)


if __name__ == '__main__':

    if len(sys.argv) != 2:
        print "No API key provided. Anonymous requests are limited!"
    else:
        api_key = sys.argv[1]

    # Call API to get outages and delays by town
    for city in cities:
        get_results_by_town(city)

    print json.dumps(results, indent=4)

    # Startup QGIS
    app = QgsApplication([], True)
    QgsApplication.setPrefixPath('/usr', True)
    QgsApplication.initQgis()

    # Init layers
    ch_layer = init_ch_layer()
    features_layer = init_features_layer()
    configure_labels(features_layer, lbl_name)

    # Register layers
    QgsMapLayerRegistry.instance().addMapLayer(features_layer)
    QgsMapLayerRegistry.instance().addMapLayer(ch_layer)

    # Setup and show canvas
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
