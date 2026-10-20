<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="AllStyleCategories" version="3.28.0">
  <pipe>
    <rasterrenderer type="paletted" band="1" opacity="1">
      <colorPalette>
        <paletteEntry value="1" color="#006400" label="1. Forest" alpha="255"/>
        <paletteEntry value="2" color="#0000FF" label="2. River" alpha="255"/>
        <paletteEntry value="3" color="#32CD32" label="3. Cropland" alpha="255"/>
        <paletteEntry value="4" color="#F4A460" label="4. Fallowland" alpha="255"/>
        <paletteEntry value="5" color="#9ACD32" label="5. Land with scrub" alpha="255"/>
        <paletteEntry value="6" color="#D2B48C" label="6. Land without scrub" alpha="255"/>
        <paletteEntry value="7" color="#FF0000" label="7. Built-up / settlements" alpha="255"/>
        <paletteEntry value="8" color="#808080" label="8. Barren land / Rocky" alpha="255"/>
        <paletteEntry value="9" color="#06b6d4" label="9. Tanks" alpha="255"/>
      </colorPalette>
    </rasterrenderer>
    <brightnesscontrast brightness="0" contrast="0"/>
    <huesaturation colorizeGreen="128" colorizeOn="0" colorizeRed="255" saturation="0" grayscaleMode="0" colorizeStrength="100" colorizeBlue="128"/>
    <rasterresampler maxOversampling="2"/>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
