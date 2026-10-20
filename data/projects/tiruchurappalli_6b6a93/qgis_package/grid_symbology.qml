<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="AllStyleCategories" version="3.28.0">
  <renderer-v2 attr="grid_type" type="categorizedSymbol">
    <categories>
      <category symbol="0" value="Non-Validation (Training) Grid" label="Non-Validation / Training Grids (70%)" render="true"/>
      <category symbol="1" value="Validation Grid" label="Validation Grids (30% Holdout)" render="true"/>
    </categories>
    <symbols>
      <symbol name="0" type="fill" clip_to_extent="1" alpha="1" force_rhr="0">
        <layer class="SimpleFill" locked="0" pass="0" enabled="1">
          <prop k="color" v="16,185,129,50"/>
          <prop k="outline_color" v="5,150,105,255"/>
          <prop k="outline_style" v="solid"/>
          <prop k="outline_width" v="0.5"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="solid"/>
        </layer>
      </symbol>
      <symbol name="1" type="fill" clip_to_extent="1" alpha="1" force_rhr="0">
        <layer class="SimpleFill" locked="0" pass="0" enabled="1">
          <prop k="color" v="245,158,11,65"/>
          <prop k="outline_color" v="217,119,6,255"/>
          <prop k="outline_style" v="dash"/>
          <prop k="outline_width" v="0.7"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="solid"/>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
</qgis>
