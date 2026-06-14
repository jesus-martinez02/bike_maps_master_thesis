import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';


const map = new maplibregl.Map({
  container: 'map',
  style: 'https://tiles.versatiles.org/assets/styles/graybeard/style.json',
  center: [15.43, 47.07],
  zoom: 12
});


map.on('load', () => {
    [
    'label-place-neighbourhood',
    'label-place-city',
    'label-place-town',
    'label-place-quarter',
    'label-place-suburb',
    'label-place-town',
    'label-place-village'
    ].forEach(layerId => {
    if (map.getLayer(layerId)) {
      map.setLayoutProperty(
        layerId,
        'visibility',
        'none'
      );
    }
  });

});
const data_table = 'final_schematic_maps'
const point_table = 'final_schematic_points'


const MAP_VERSION = 5;



map.on("load", () => {
  // LINE SOURCE
  map.addSource("features", {
    type: "vector",
    tiles: [
      'https://martin-tiles.librebikemaps.com/final_schematic_maps/{z}/{x}/{y}?v=12'
    ],
    minzoom: 0,
    maxzoom: 14,
  });

  map.addSource("points", {
    type: "vector",
    tiles: [
      'https://martin-tiles.librebikemaps.com/final_schematic_points/{z}/{x}/{y}?v=12'
    ],
    minzoom: 0,
    maxzoom: 14,
  });

  map.addLayer({
    id: "all_features",
    type: "line",
    source: "features",
    "source-layer": data_table,
    paint: {
      "line-color": "#036bfc",
      "line-width": 2,
    },
  });

  map.addLayer({
    id: "stations",
    type: "symbol",
    source: "points",
    "source-layer": point_table,

    layout: {
      "icon-image": "marker-15",
      "icon-size": 1,

      "text-field": ["get", "name"],
      "text-size": 8,
      "text-offset": [0, 1.2],
      "text-anchor": "top",
    },

    paint: {
      "text-color": "#000",
      "text-halo-color": "#fff",
      "text-halo-width": 1,
    },
  });

  map.addLayer({
  id: "station_points",
  type: "circle",
  source: "points",
  "source-layer": point_table,

  paint: {
    "circle-radius": 3,
    "circle-color": "#ffffff",
    "circle-stroke-color": "#036bfc",
    "circle-stroke-width": 3,
  },
});

});