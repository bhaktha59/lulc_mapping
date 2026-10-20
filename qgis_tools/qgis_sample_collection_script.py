"""
QGIS Ground-Truth Digitization Assistant Script
Run this script inside the QGIS Python Console (Plugins -> Python Console or Ctrl+Alt+P).
It automatically:
1. Creates a formatted memory point layer ('TN_LULC_Ground_Truth_Samples') in EPSG:4326.
2. Configures 'class_id' (1-8) and 'class_name' attribute fields.
3. Applies official color symbology for all 8 Tamil Nadu LULC classes.
4. Enables easy digitizing on top of Google Satellite / ESRI Imagery basemaps.
"""

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsMarkerSymbol,
    QgsSimpleMarkerSymbolLayer,
)
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QColor

LULC_PALETTE = {
    1: {"name": "Forest", "color": QColor(0, 100, 0)},
    2: {"name": "Waterbodies", "color": QColor(0, 0, 255)},
    3: {"name": "Cropland", "color": QColor(50, 205, 50)},
    4: {"name": "Fallowland", "color": QColor(244, 164, 96)},
    5: {"name": "Land with scrub", "color": QColor(154, 205, 50)},
    6: {"name": "Land without scrub", "color": QColor(210, 180, 140)},
    7: {"name": "Built-up / settlements", "color": QColor(255, 0, 0)},
    8: {"name": "Barren land / Rocky", "color": QColor(128, 128, 128)},
}

def create_ground_truth_layer():
    layer = QgsVectorLayer("Point?crs=epsg:4326", "TN_LULC_Ground_Truth_Samples", "memory")
    pr = layer.dataProvider()
    pr.addAttributes([
        QgsField("class_id", QVariant.Int),
        QgsField("class_name", QVariant.String),
    ])
    layer.updateFields()

    # Symbology
    categories = []
    for cid, cinfo in LULC_PALETTE.items():
        symbol = QgsMarkerSymbol.createSimple({
            "name": "circle",
            "size": "4.5",
            "color": f"{cinfo['color'].red()},{cinfo['color'].green()},{cinfo['color'].blue()},255",
            "outline_color": "255,255,255,255",
            "outline_width": "0.6",
        })
        category = QgsRendererCategory(cid, symbol, f"{cid}. {cinfo['name']}")
        categories.append(category)

    renderer = QgsCategorizedSymbolRenderer("class_id", categories)
    layer.setRenderer(renderer)
    layer.triggerRepaint()

    QgsProject.instance().addMapLayer(layer)
    layer.startEditing()
    print("TN_LULC_Ground_Truth_Samples layer successfully added! Toggle 'Add Point Feature' to begin digitizing.")

if __name__ == "__main__":
    create_ground_truth_layer()
