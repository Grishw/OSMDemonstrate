// Цвета для разных алгоритмов
const algorithmColors = {
    'dijkstra': '#ff0000',     // Красный
    'astar': '#0000ff',        // Синий
    'dijkstra_comparison': '#ff4444', // Светло-красный
    'astar_comparison': '#4444ff'     // Светло-синий
};

// Стили для маршрутов сравнения
function getComparisonRouteStyle(feature) {
    const algorithm = feature.properties.algorithm;
    const baseColor = algorithmColors[algorithm] || '#888888';
    
    if (feature.geometry.type === 'Point') {
        return {
            color: baseColor,
            fillColor: baseColor,
            radius: 8,
            fillOpacity: 1,
            weight: 2,
            opacity: 1,
            pane: 'routePane'
        };
    } else {
        return {
            color: baseColor,
            weight: 6,
            opacity: 0.8,
            lineJoin: 'round',
            lineCap: 'round',
            pane: 'routePane',
            dashArray: algorithm === 'dijkstra_comparison' ? '5, 5' : null
        };
    }
}

// Запрос всех маршрутов для сравнения
function requestRouteComparison() {
    const startInput = document.getElementById('start').value.trim();
    const endInput = document.getElementById('end').value.trim();

    try {
        const start = parseCoordinates(startInput);
        const end = parseCoordinates(endInput);

        const requestBody = { start, end };

        document.getElementById('status').textContent = 'Сравнение алгоритмов...';

        // Запросы для обоих алгоритмов
        const dijkstraPromise = fetch('/api/route', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        const astarPromise = fetch('/api/route/astar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        const startTime = performance.now();

        // Выполняем оба запроса параллельно
        Promise.all([dijkstraPromise, astarPromise])
            .then(responses => Promise.all(responses.map(r => r.json())))
            .then(results => {
                const endTime = performance.now();
                const totalExecutionTime = (endTime - startTime) / 1000;
                
                document.getElementById('status').textContent = '';
                
                const [dijkstraData, astarData] = results;
                
                if (dijkstraData.status === 'ok' && astarData.status === 'ok') {
                    displayComparisonResults(dijkstraData, astarData, totalExecutionTime);
                } else {
                    const errors = [];
                    if (dijkstraData.status !== 'ok') errors.push(`Дейкстра: ${dijkstraData.message}`);
                    if (astarData.status !== 'ok') errors.push(`A*: ${astarData.message}`);
                    alert(`Ошибки:\n${errors.join('\n')}`);
                }
            })
            .catch(error => {
                document.getElementById('status').textContent = '';
                console.error("Ошибка при сравнении маршрутов:", error);
                alert("Ошибка при сравнении маршрутов");
            });

    } catch (error) {
        document.getElementById('status').textContent = '';
        alert(error.message);
    }
}

// Отображение результатов сравнения
function displayComparisonResults(dijkstraData, astarData, totalExecutionTime) {
    // Очищаем предыдущие маршруты
    if (window.comparisonLayers) {
        window.comparisonLayers.forEach(layer => {
            if (layer) map.removeLayer(layer);
        });
    }
    window.comparisonLayers = [];
    clearRoadPoints();

    // Подготавливаем данные для отображения с уникальными идентификаторами алгоритмов
    const dijkstraRoute = prepareComparisonRouteData(dijkstraData, 'dijkstra_comparison');
    const astarRoute = prepareComparisonRouteData(astarData, 'astar_comparison');

    // Создаем слои для каждого алгоритма
    const dijkstraLayer = L.geoJSON(dijkstraRoute, {
        pane: 'routePane',
        style: getComparisonRouteStyle,
        pointToLayer: createComparisonPointMarker,
        onEachFeature: bindComparisonPopup
    }).addTo(map);

    const astarLayer = L.geoJSON(astarRoute, {
        pane: 'routePane',
        style: getComparisonRouteStyle,
        pointToLayer: createComparisonPointMarker,
        onEachFeature: bindComparisonPopup
    }).addTo(map);

    window.comparisonLayers.push(dijkstraLayer, astarLayer);

    // Масштабируем карту по всем маршрутам
    const allBounds = [dijkstraLayer.getBounds(), astarLayer.getBounds()];
    const combinedBounds = allBounds.reduce((bounds, current) => {
        return bounds.extend(current);
    });
    
    if (combinedBounds.isValid()) {
        map.fitBounds(combinedBounds.pad(0.1));
    }

    // Показываем сводную информацию
    showComparisonSummary(dijkstraData.summary, astarData.summary, totalExecutionTime);
}

// Подготовка данных маршрута для сравнения
function prepareComparisonRouteData(routeData, algorithmId) {
    const features = routeData.route.features.map(feature => {
        return {
            ...feature,
            properties: {
                ...feature.properties,
                algorithm: algorithmId,
                original_algorithm: feature.properties.algorithm
            }
        };
    });
    
    return {
        ...routeData.route,
        features: features
    };
}

// Создание маркеров для точек сравнения
function createComparisonPointMarker(feature, latlng) {
    const style = getComparisonRouteStyle(feature);
    const marker = L.circleMarker(latlng, style);
    
    const algorithmName = feature.properties.original_algorithm === 'A*' ? 'A*' : 'Дейкстра';
    const pointType = feature.properties.type === 'start_point' ? 'Начало' : 'Конец';
    
    marker.bindPopup(`${pointType} (${algorithmName})`);
    
    return marker;
}

// Всплывающее окно для сегментов сравнения
function bindComparisonPopup(feature, layer) {
    if (feature.properties && feature.properties.name) {
        const algorithmName = feature.properties.original_algorithm === 'A*' ? 'A* (эвристический)' : 'Дейкстра (точный)';
        const lengthText = feature.properties.length_m ? `<br>Длина: ${feature.properties.length_m.toFixed(1)} м` : '';
        
        layer.bindPopup(`
            <b>${feature.properties.name || 'Без названия'}</b><br>
            Алгоритм: ${algorithmName}<br>
            Тип: ${feature.properties.highway || 'road'}<br>
            Стоимость: ${feature.properties.cost ? feature.properties.cost.toFixed(2) + ' сек.' : ''}${lengthText}
        `);
    }
}

// Отображение сводной информации о сравнении
function showComparisonSummary(dijkstraSummary, astarSummary, totalExecutionTime) {
    const dijkstraTime = dijkstraSummary.execution_time ? dijkstraSummary.execution_time.toFixed(3) : 'неизвестно';
    const astarTime = astarSummary.execution_time ? astarSummary.execution_time.toFixed(3) : 'неизвестно';
    
    const dijkstraDistance = dijkstraSummary.total_distance ? dijkstraSummary.total_distance.toFixed(1) : 'неизвестна';
    const astarDistance = astarSummary.total_distance ? astarSummary.total_distance.toFixed(1) : 'неизвестна';
    
    const dijkstraCost = dijkstraSummary.total_cost ? dijkstraSummary.total_cost.toFixed(1) : 'неизвестна';
    const astarCost = astarSummary.total_cost ? astarSummary.total_cost.toFixed(1) : 'неизвестна';
    
    const efficiency = dijkstraSummary.execution_time && astarSummary.execution_time ? 
        (dijkstraSummary.execution_time / astarSummary.execution_time).toFixed(2) : 'неизвестно';

    document.getElementById('routeSummary').innerHTML = `
        <strong>Сравнение алгоритмов:</strong><br><br>
        
        <div style="border-left: 3px solid ${algorithmColors.dijkstra_comparison}; padding-left: 8px; margin-bottom: 10px;">
            <strong>Дейкстра:</strong><br>
            • Время выполнения: ${dijkstraTime} сек<br>
            • Длина пути: ${dijkstraDistance} м<br>
            • Общая стоимость: ${dijkstraCost} сек<br>
            • Сегментов: ${dijkstraSummary.total_segments}
        </div>
        
        <div style="border-left: 3px solid ${algorithmColors.astar_comparison}; padding-left: 8px; margin-bottom: 10px;">
            <strong>A*:</strong><br>
            • Время выполнения: ${astarTime} сек<br>
            • Длина пути: ${astarDistance} м<br>
            • Общая стоимость: ${astarCost} сек<br>
            • Сегментов: ${astarSummary.total_segments}
        </div>
        
        <div style="background: #f8f9fa; padding: 8px; border-radius: 4px;">
            <strong>Эффективность:</strong><br>
            • A* быстрее в ${efficiency} раз<br>
            • Общее время сравнения: ${totalExecutionTime.toFixed(3)} сек
        </div>
    `;
    
    document.getElementById('routeInfo').style.display = 'block';
}

// Инициализация сравнения
function initComparison() {
    // Добавляем кнопку сравнения если её нет
    if (!document.getElementById('compareBtn')) {
        const routeBtn = document.getElementById('routeBtn');
        const compareBtn = document.createElement('button');
        compareBtn.id = 'compareBtn';
        compareBtn.textContent = 'Сравнить алгоритмы';
        compareBtn.style.marginTop = '10px';
        compareBtn.style.backgroundColor = '#6c757d';
        
        routeBtn.parentNode.insertBefore(compareBtn, routeBtn.nextSibling);
        
        compareBtn.addEventListener('click', requestRouteComparison);
    }
    
    // Инициализируем глобальные переменные
    window.comparisonLayers = [];
}