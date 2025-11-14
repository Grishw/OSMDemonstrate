-- Скрипт 7: Расчет стоимостей
-- Базовая стоимость (время в секундах)
UPDATE routing_graph 
SET 
    cost = (length_m / 1000) / maxspeed_kmh * 3600,
    reverse_cost = (length_m / 1000) / maxspeed_kmh * 3600;

-- Применение одностороннего движения
UPDATE routing_graph 
SET reverse_cost = -1 
WHERE oneway_processed = 1;

-- Обратное направление
UPDATE routing_graph 
SET 
    cost = reverse_cost,
    reverse_cost = -1
WHERE oneway_processed = -1;