-- Функция для анализа всех типов пересечений
CREATE OR REPLACE FUNCTION analyze_intersection_types()
RETURNS TABLE(intersection_type TEXT, count BIGINT, description TEXT) AS $$
BEGIN
    -- Анализируем геометрические типы пересечений
    RETURN QUERY
    WITH intersection_analysis AS (
        SELECT 
            w1.id as way1_id,
            w2.id as way2_id,
            ST_Intersection(w1.linestring, w2.linestring) as intersection_geom,
            ST_GeometryType(ST_Intersection(w1.linestring, w2.linestring)) as geom_type,
            CASE 
                WHEN ST_Equals(ST_StartPoint(w1.linestring), ST_StartPoint(w2.linestring)) OR
                     ST_Equals(ST_StartPoint(w1.linestring), ST_EndPoint(w2.linestring)) OR
                     ST_Equals(ST_EndPoint(w1.linestring), ST_StartPoint(w2.linestring)) OR
                     ST_Equals(ST_EndPoint(w1.linestring), ST_EndPoint(w2.linestring)) THEN 'endpoint'
                WHEN ST_Crosses(w1.linestring, w2.linestring) THEN 'crossing'
                WHEN ST_Overlaps(w1.linestring, w2.linestring) THEN 'overlap'
                ELSE 'other'
            END as intersection_category
        FROM ways w1, ways w2 
        WHERE w1.id < w2.id 
            AND ST_Intersects(w1.linestring, w2.linestring)
            AND NOT ST_Touches(w1.linestring, w2.linestring)
    )
    SELECT 
        geom_type as intersection_type,
        COUNT(*) as count,
        intersection_category as description
    FROM intersection_analysis
    GROUP BY geom_type, intersection_category
    ORDER BY COUNT(*) DESC;
END;
$$ LANGUAGE plpgsql;

-- Запустим анализ
SELECT * FROM analyze_intersection_types();