import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { graybeard } from '@versatiles/style';


const map = new maplibregl.Map({
  container: 'map',
  style: 'https://tiles.versatiles.org/assets/styles/colorful/style.json',
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

  const style = map.getStyle();
  
  console.table(
    style.layers.map(layer => ({
      id: layer.id,
      type: layer.type
    }))
  );
});



// 

const currentUrl = window.location.origin; 


const data_table = 'final_table'

map.on('click', (e) => {
  const features = map.queryRenderedFeatures(e.point, {
    layers: ['features-Track']
  });
  console.log(features.map(f => f.properties.new_percentile));
});

const MAP_VERSION = 5;


map.on('load', () => {
  map.addSource('features', {
    type: 'vector',
    tiles: [
      'https://martin-tiles.librebikemaps.com/final_table/{z}/{x}/{y}?v=28'
    ],
    minzoom: 0,
    maxzoom: 14
  });


  
  let sliderValue = 0;
  const slider = document.getElementById('percentileSlider');

  map.addLayer({
    id: 'features-Track',
    type: 'line',
    source: 'features',
    'source-layer': data_table,
    filter: [
    'all',
    ['==', ['get', 'category'], 'Track'],
    ['>=', ['get', 'new_percentile'], sliderValue]
    ],
    paint: {
      'line-color': '#036bfc',
      'line-width': 2
    }
  });

    map.addLayer({
    id: 'features-Right_Track',
    type: 'line',
    source: 'features',
    'source-layer': data_table,
    filter: [
    'all',
    ['==', ['get', 'category'], 'Right_Track'],
    ['>=', ['get', 'new_percentile'], sliderValue]
    ],
    paint: {
      'line-color': '#036bfc',
      'line-width': 2
    }
  });

    map.addLayer({
    id: 'features-Left_Track',
    type: 'line',
    source: 'features',
    'source-layer': data_table,
    filter: [
    'all',
    ['==', ['get', 'category'], 'Left_Track'],
    ['>=', ['get', 'new_percentile'], sliderValue]
    ],
    paint: {
      'line-color': '#036bfc',
      'line-width': 2
    }
  });

    map.addLayer({
    id: 'features-Track_shared',
    type: 'line',
    source: 'features',
    'source-layer': data_table,
    filter: [
    'all',
    ['==', ['get', 'category'], 'Track_shared'],
    ['>=', ['get', 'new_percentile'], sliderValue]
    ],
    paint: {
      'line-color': '#08d8fc',
      'line-width': 2
    }
  });

    map.addLayer({
    id: 'features-Cycling_Street',
    type: 'line',
    source: 'features',
    'source-layer': data_table,
    filter: [
    'all',
    ['==', ['get', 'category'], 'Cycling_Street'],
    ['>=', ['get', 'new_percentile'], sliderValue]
    ],
    paint: {
      'line-color': '#ce52f7',
      'line-width': 2
    }
  });

    map.addLayer({
    id: 'features-Crossing',
    type: 'line',
    source: 'features',
    'source-layer': data_table,
    filter: [
    'all',
    ['==', ['get', 'category'], 'Crossing'],
    ['>=', ['get', 'new_percentile'], sliderValue]
    ],
    paint: {
      'line-color': '#f0ec18',
      'line-width': 2
    }
    });

    map.addLayer({
    id: 'features-Lane',
    type: 'line',
    source: 'features',
    'source-layer': data_table,
    filter: [
    'all',
    ['==', ['get', 'category'], 'Lane'],
    ['>=', ['get', 'new_percentile'], sliderValue]
    ],
    paint: {
      'line-color': '#72f261',
      'line-width': 2
    }
    });


    map.addLayer({
    id: 'features-Left_Lane',
    type: 'line',
    source: 'features',
    'source-layer': data_table,
    filter: [
    'all',
    ['==', ['get', 'category'], 'Left_Lane'],
    ['>=', ['get', 'new_percentile'], sliderValue]
    ],
    paint: {
      'line-color': '#8fe3a5',
      'line-width': 2
    }
  });

    map.addLayer({
    id: 'features-Right_Lane',
    type: 'line',
    source: 'features',
    'source-layer': data_table,
    filter: [
    'all',
    ['==', ['get', 'category'], 'Right_Lane'],
    ['>=', ['get', 'new_percentile'], sliderValue]
    ],
    paint: {
      'line-color': '#1f5c2f',
      'line-width': 2
    }
    });


  map.addLayer({
    id: 'features-Unpaved',
    type: 'line',
    source: 'features',
    'source-layer': data_table,
    filter: [
    'all',
    ['==', ['get', 'category'], 'Unpaved'],
    ['>=', ['get', 'new_percentile'], sliderValue]
    ],
    paint: {
      'line-color': '#826423',
      'line-width': 2
    }
  });

  map.addLayer({
    id: 'features-Street',
    type: 'line',
    source: 'features',
    'source-layer': data_table,
    filter: [
    'all',
    ['==', ['get', 'category'], 'Street'],
    ['>=', ['get', 'new_percentile'], sliderValue]
    ],
    paint: {
      'line-color': '#a6a09f',
      'line-width': 2
    }
  });


    map.addLayer({
    id: 'features-Shared_Lane',
    type: 'line',
    source: 'features',
    'source-layer': data_table,
    filter: [
    'all',
    ['==', ['get', 'category'], 'Shared_Lane'],
    ['>=', ['get', 'new_percentile'], sliderValue]
    ],
    paint: {
      'line-color': '#f2cf07',
      'line-width': 2
    }
  });

    map.addLayer({
    id: 'features-Right_Shared_Lane',
    type: 'line',
    source: 'features',
    'source-layer': data_table,
    filter: [
    'all',
    ['==', ['get', 'category'], 'Right_Shared_Lane'],
    ['>=', ['get', 'new_percentile'], sliderValue]
    ],
    paint: {
      'line-color': '#f2cf07',
      'line-width': 2
    }
  });
  


      map.addLayer({
    id: 'features-Left_Shared_Lane',
    type: 'line',
    source: 'features',
    'source-layer': data_table,
    filter: [
    'all',
    ['==', ['get', 'category'], 'Left_Shared_Lane'],
    ['>=', ['get', 'new_percentile'], sliderValue]
    ],
    paint: {
      'line-color': '#f2cf07',
      'line-width': 2
    }
  });
  //   map.addLayer({
  //   id: 'features-ignore',
  //   type: 'line',
  //   source: 'features',
  //   'source-layer': data_table,
  //   filter: ['==', ['get', 'category'], 'ignore'],
  //   paint: {
  //     'line-color': '#000000',
  //     'line-width': 2
  //   }
  // });



  //   map.addLayer({
  //   id: 'features-Other',
  //   type: 'line',
  //   source: 'features',
  //   'source-layer': data_table,
  //   filter: ['==', ['get', 'category'], 'Other'],
  //   paint: {
  //     'line-color': '#7777ff',
  //     'line-width': 2
  //   }
  // });
  
  const categories = ['Track', 'Right_Track', 'Left_Track', 'Track_shared', 'Cycling_Street', 'Crossing', 'Lane', 
    'Left_Lane', 'Right_Lane', 'Shared_Lane','Left_Shared_Lane', 'Right_Shared_Lane','Unpaved', 'Street'];

  const label = document.getElementById('sliderLabel');

  function updateSliderUI(value) {
  label.textContent = `${value}%`;
  
  }
  slider.addEventListener('input', (e) => {
    const sliderValue = Number(e.target.value) / 100;

    categories.forEach((cat) => {
      map.setFilter(`features-${cat}`, [
        'all',
        ['==', ['get', 'category'], cat],
        ['>=', ['get', 'new_percentile'], sliderValue]
      ]);
        updateSliderUI(e.target.value);
    });
  });

  });

function updateFilter() {
  document.querySelectorAll('#filters input').forEach(input => {
    map.setLayoutProperty(
      `features-${input.value}`,
      'visibility',
      input.checked ? 'visible' : 'none'
    );
  });
}

document
  .querySelectorAll('#filters input')
  .forEach(el => el.addEventListener('change', updateFilter));


function locateUser() {
  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lng = position.coords.longitude;
      const lat = position.coords.latitude;

      map.setCenter([lng, lat]);
      map.setZoom(15);

      new maplibregl.Marker({
        element: createUserMarker()
      })
      .setLngLat([lng, lat])
      .addTo(map);
    },
    (error) => {
      console.error("Geolocation error:", error);
      alert("Location error: " + error.message);
    },
    { enableHighAccuracy: true }
  );
}

window.locateUser = locateUser;

function createUserMarker() {
  const el = document.createElement('div');
  el.style.width = '12px';
  el.style.height = '12px';
  el.style.backgroundColor = '#007aff';
  el.style.borderRadius = '50%';
  el.style.border = '2px solid white';
  el.style.boxShadow = '0 0 6px rgba(0,0,0,0.3)';
  return el;
}

if ("geolocation" in navigator) {
  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lng = position.coords.longitude;
      const lat = position.coords.latitude;

      map.setCenter([lng, lat]);
      map.setZoom(15);

      new maplibregl.Marker({
        element: createUserMarker()
      })
      .setLngLat([lng, lat])
      .addTo(map);
    },
    (error) => {
      console.error("Geolocation error:", error);
    },
    {
      enableHighAccuracy: true
    }
  );
} else {
  console.log("Geolocation not supported.");
}


