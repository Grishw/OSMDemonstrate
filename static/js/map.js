// Инициализация карты и базовых функций
const map = L.map("map").setView([55.75, 37.61], 10);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
}).addTo(map);

let startMarker = null;
let endMarker = null; 
let roadStartMarker = null;
let roadEndMarker = null;

// Создаем отдельные панели для правильного порядка слоев
if (!map.getPane('roadsPane')) {
  map.createPane('roadsPane');
  map.getPane('roadsPane').style.zIndex = 450; // Между tileLayer (400) и маркерами (600)
}



// Слои для дорог и маршрута
let roadsLayer = L.geoJSON(null, {
  pane: 'roadsPane'
}).addTo(map);


// Установка координат в поле ввода
function setField(id, latlng) {
  document.getElementById(id).value = latlng.lat.toFixed(6) + ', ' + latlng.lng.toFixed(6);
}

// Очистка точек дорожной сети
function clearRoadPoints() {
  if (roadStartMarker) {
    map.removeLayer(roadStartMarker);
    roadStartMarker = null;
  }
  if (roadEndMarker) {
    map.removeLayer(roadEndMarker);
    roadEndMarker = null;
  }
}
// Очистка маршрута
function clearRoute() {
  routeLayer.clearLayers();
  clearRoadPoints();
  document.getElementById('routeInfo').style.display = 'none';
}

// Обработчик кликов по карте
map.on('click', function(e){
  if (!startMarker) {
    startMarker = L.marker(e.latlng, {draggable: true})
      .addTo(map)
      .bindPopup('Начальная точка')
      .openPopup();
    setField('start', e.latlng);
    startMarker.on('dragend', ev => setField('start', ev.target.getLatLng()));
    clearRoute();
  } else if (!endMarker) {
    endMarker = L.marker(e.latlng, {draggable: true})
      .addTo(map)
      .bindPopup('Конечная точка')
      .openPopup();
    setField('end', e.latlng);
    endMarker.on('dragend', ev => setField('end', ev.target.getLatLng()));
    clearRoute();
  } else {
    const d1 = map.distance(e.latlng, startMarker.getLatLng());
    const d2 = map.distance(e.latlng, endMarker.getLatLng());
    if (d1 < d2) {
      startMarker.setLatLng(e.latlng);
      setField('start', e.latlng);
    } else {
      endMarker.setLatLng(e.latlng);
      setField('end', e.latlng);
    }
    clearRoute();
  }
});

// Загрузка дорог на карту
function loadWays() {
  const showRoads = document.getElementById('showRoads').checked;
  
  if (!showRoads) {
    roadsLayer.clearLayers();
    return;
  }

  const bounds = map.getBounds();
  const zoom = map.getZoom();
  const bbox = [
    bounds.getWest(),
    bounds.getSouth(), 
    bounds.getEast(),
    bounds.getNorth()
  ].join(",");

  const url = `/api/ways?bbox=${bbox}&zoom=${zoom}`;

  fetch(url)
    .then(response => response.json())
    .then(data => {
      // Полностью пересоздаем слой с данными и стилями
      roadsLayer.clearLayers();
      roadsLayer.addData(data);
      
      roadsLayer = L.geoJSON(data, {
        pane: 'roadsPane',
        style: {
          color: '#8A2BE2',
          weight: 3,
          opacity: 0.7
        }
      }).addTo(map);

    })
    .catch(error => {
      console.error("Ошибка загрузки дорог:", error);
    });
}

// Переключение видимости дорог
function toggleRoadsVisibility() {
  const showRoads = document.getElementById('showRoads').checked;
  
  if (showRoads) {
    loadWays();
  } else {
    map.removeLayer(window.roadsLayer);
  }
}

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('showRoads').addEventListener('change', toggleRoadsVisibility);
});

// Инициализация
map.on("moveend", loadWays);
loadWays();