-- Проверим количество дорог по типам
SELECT tags->'highway' as road_type, COUNT(*)
FROM ways 
WHERE tags ? 'highway'
GROUP BY tags->'highway'
ORDER BY COUNT(*) DESC;

-- Проверим наличие одностороннего движения
SELECT tags->'oneway' as oneway, COUNT(*)
FROM ways 
WHERE tags ? 'highway'
GROUP BY tags->'oneway';

-- Проверим теги доступа для автомобилей
SELECT tags->'motor_vehicle' as motor_vehicle, COUNT(*)
FROM ways 
WHERE tags ? 'highway'
GROUP BY tags->'motor_vehicle';