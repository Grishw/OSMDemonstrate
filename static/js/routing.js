// Создаем панель для маршрута с максимальным z-index
if (!map.getPane('routePane')) {
  map.createPane('routePane');
  map.getPane('routePane').style.zIndex = 1000; // Максимальный приоритет
}

let routeLayer = L.geoJSON(null, {
  pane: 'routePane'
}).addTo(map);

// Парсинг координат из строки
function parseCoordinates(str) {
  const parts = str.split(',').map(x => parseFloat(x.trim()));
  if (parts.length !== 2 || isNaN(parts[0]) || isNaN(parts[1])) {
    alert("Введите координаты в формате: широта, долгота");
    throw new Error("Неверный формат координат");
  }
  return [parts[0], parts[1]];
}

// Отображение информации о маршруте
function showRouteInfo(summary) {
  const algorithmName = summary.algorithm === 'A*' ? 'A* (эвристический)' : 
                       summary.algorithm === 'Dijkstra' ? 'Дейкстра (точный)' : 
                       'Неизвестный алгоритм';
  
  const totalDistance = summary.total_distance ? `${summary.total_distance.toFixed(2)} м` : 'не указана';
  const executionTime = summary.execution_time ? `${summary.execution_time.toFixed(3)} сек` : 'не указано';
  
  document.getElementById('routeSummary').innerHTML = 
    `<strong>Информация о маршруте:</strong><br>
     Алгоритм: ${algorithmName}<br>
     Сегментов: ${summary.total_segments}<br>
     Длина пути: ${totalDistance}<br>
     Общее время: ${summary.total_cost ? summary.total_cost.toFixed(1) + ' сек' : 'не указано'}<br>
     Время выполнения: ${executionTime}`;
  
  // Показываем панель информации
  document.getElementById('routeInfo').style.display = 'block';
}

// Стили для маршрута с повышенной видимостью
function getRouteStyle(feature) {
  if (feature.geometry.type === 'Point') {
    return {
      color: feature.properties.type === 'start_point' ? '#00ff00' : '#0000ff',
      fillColor: feature.properties.type === 'start_point' ? '#00ff00' : '#0000ff',
      radius: 10, // Увеличиваем радиус для лучшей видимости
      fillOpacity: 1,
      weight: 3,
      opacity: 1,
      pane: 'routePane' // Явно указываем панель
    };
  } else if (feature.properties.type === 'full_route') {
    return {
      color: '#ff0000',
      weight: 8, // Увеличиваем толщину
      opacity: 0.9,
      lineJoin: 'round',
      lineCap: 'round',
      pane: 'routePane'
    };
  } else {
    return {
      color: '#00ff00',
      weight: 6,
      opacity: 1,
      dashArray: '5, 5',
      pane: 'routePane'
    };
  }
}

// Создание маркера для точек с использованием routePane
function createPointMarker(feature, latlng) {
  const style = getRouteStyle(feature);
  
  if (feature.properties.type === 'start_point') {
    roadStartMarker = L.circleMarker(latlng, {
      ...style,
      pane: 'routePane'
    }).addTo(map).bindPopup('Начальная точка дорожной сети');
    return roadStartMarker;
  } else if (feature.properties.type === 'end_point') {
    roadEndMarker = L.circleMarker(latlng, {
      ...style,
      pane: 'routePane'
    }).addTo(map).bindPopup('Конечная точка дорожной сети');
    return roadEndMarker;
  }
}

// Всплывающее окно для сегментов маршрута
function bindRoutePopup(feature, layer) {
  if (feature.properties && feature.properties.name) {
    const algorithmText = feature.properties.algorithm ? `<br>Алгоритм: ${feature.properties.algorithm}` : '';
    layer.bindPopup(`
      <b>${feature.properties.name || 'Без названия'}</b><br>
      Тип: ${feature.properties.highway || 'road'}<br>
      Стоимость: ${feature.properties.cost ? feature.properties.cost.toFixed(2) + ' сек.' : ''}${algorithmText}
    `);
  }
}
// Функция очистки точек маршрута
function clearRoadPoints() {
  if (window.roadStartMarker) {
    map.removeLayer(window.roadStartMarker);
    window.roadStartMarker = null;
  }
  if (window.roadEndMarker) {
    map.removeLayer(window.roadEndMarker);
    window.roadEndMarker = null;
  }
}

// Отображение маршрута на карте
function displayRoute(routeData) {
  // Удаляем предыдущий маршрут
  if (window.routeLayer) {
    map.removeLayer(window.routeLayer);
  }
  clearRoadPoints();

  // Создаем новый слой маршрута с явным указанием панели
  window.routeLayer = L.geoJSON(routeData, {
    pane: 'routePane', // Явно указываем панель
    style: getRouteStyle,
    pointToLayer: createPointMarker,
    onEachFeature: bindRoutePopup
  }).addTo(map);

  // Принудительно поднимаем слой наверх
  window.routeLayer.bringToFront();

  // Масштабируем карту по маршруту
  if (window.routeLayer.getBounds().isValid()) {
    map.fitBounds(window.routeLayer.getBounds().pad(0.1));
  }

  // Дополнительная гарантия - поднимаем все маркеры
  setTimeout(() => {
    if (window.roadStartMarker) window.roadStartMarker.bringToFront();
    if (window.roadEndMarker) window.roadEndMarker.bringToFront();
    if (window.routeLayer) window.routeLayer.bringToFront();
  }, 100);
}

// Запрос маршрута к серверу
function requestRoute() {
  const startInput = document.getElementById('start').value.trim();
  const endInput = document.getElementById('end').value.trim();
  const algorithm = document.getElementById('algorithm').value;

  try {
    const start = parseCoordinates(startInput);
    const end = parseCoordinates(endInput);

    const requestBody = { start, end };

    document.getElementById('status').textContent = 'Построение маршрута...';

    // Выбираем endpoint в зависимости от алгоритма
    const endpoint = algorithm === 'astar' ? '/api/route/astar' : '/api/route';

    // Замеряем время выполнения на клиенте
    const startTime = performance.now();

    fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    })
      .then(response => response.json())
      .then(data => {
        const endTime = performance.now();
        const clientExecutionTime = (endTime - startTime) / 1000; // в секундах
        
        document.getElementById('status').textContent = '';

        if (data.status === 'ok' && data.route) {
          // Добавляем время выполнения в данные summary
          if (data.summary) {
            data.summary.execution_time = clientExecutionTime;
          }
          displayRoute(data.route);
          if (data.summary) {
            showRouteInfo(data.summary);
          }
        } else {
          alert(data.message || "Маршрут не найден");
        }
      })
      .catch(error => {
        document.getElementById('status').textContent = '';
        console.error("Ошибка при запросе маршрута:", error);
        alert("Ошибка при запросе маршрута");
      });

  } catch (error) {
    document.getElementById('status').textContent = '';
    alert(error.message);
  }
}

// Функция для расчета общей длины маршрута
function calculateTotalDistance(routeData) {
  let totalDistance = 0;
  if (routeData && routeData.features) {
    routeData.features.forEach(feature => {
      if (feature.geometry && feature.geometry.type === 'LineString' && feature.properties && feature.properties.cost) {
        // Предполагаем, что cost пропорционален расстоянию
        totalDistance += feature.properties.cost * 1000; // примерное преобразование
      }
    });
  }
  return totalDistance;
}

// Инициализация обработчиков событий
document.addEventListener('DOMContentLoaded', function() {
  // Инициализация глобальных переменных
  window.routeLayer = null;
  window.roadStartMarker = null;
  window.roadEndMarker = null;

  document.getElementById('routeBtn').addEventListener("click", requestRoute);
  document.getElementById('closeInfo').addEventListener("click", function() {
    document.getElementById('routeInfo').style.display = 'none';
  });

  initComparison();

  // Обработчик для очистки маршрута при изменении карты
  map.on('layeradd', function(e) {
    // Если добавляется новый слой, поднимаем маршрут наверх
    if (window.routeLayer && e.layer !== window.routeLayer) {
      setTimeout(() => {
        if (window.routeLayer) window.routeLayer.bringToFront();
        if (window.roadStartMarker) window.roadStartMarker.bringToFront();
        if (window.roadEndMarker) window.roadEndMarker.bringToFront();
      }, 50);
    }
  });
});