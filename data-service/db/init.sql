-- Initialize RailOptima database with PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_stations_code ON stations(code);
CREATE INDEX IF NOT EXISTS idx_stations_location ON stations USING GIST(ST_Point(longitude, latitude));
CREATE INDEX IF NOT EXISTS idx_trains_number ON trains(train_number);
CREATE INDEX IF NOT EXISTS idx_trains_status ON trains(status);
CREATE INDEX IF NOT EXISTS idx_train_events_train_id ON train_events(train_id);
CREATE INDEX IF NOT EXISTS idx_train_events_created_at ON train_events(created_at);
CREATE INDEX IF NOT EXISTS idx_timetable_entries_train_id ON timetable_entries(train_id);
CREATE INDEX IF NOT EXISTS idx_timetable_entries_station_id ON timetable_entries(station_id);

-- Insert sample data for testing
INSERT INTO stations (code, name, latitude, longitude, platforms) VALUES
('NDLS', 'New Delhi', 28.6448, 77.2097, 16),
('GZB', 'Ghaziabad', 28.6692, 77.4538, 6),
('MB', 'Moradabad', 28.8386, 78.7733, 4),
('BE', 'Bareilly', 28.3670, 79.4304, 3),
('LKO', 'Lucknow', 26.8467, 80.9462, 6),
('CNB', 'Kanpur Central', 26.4499, 80.3319, 10)
ON CONFLICT (code) DO NOTHING;

-- Insert sample tracks
INSERT INTO tracks (segment_id, from_station_id, to_station_id, distance_km, max_speed_kmh, is_electrified, track_type) 
SELECT 
    'NDLS-GZB-001',
    (SELECT id FROM stations WHERE code = 'NDLS'),
    (SELECT id FROM stations WHERE code = 'GZB'),
    46.0, 130, true, 'double'
WHERE NOT EXISTS (SELECT 1 FROM tracks WHERE segment_id = 'NDLS-GZB-001');

INSERT INTO tracks (segment_id, from_station_id, to_station_id, distance_km, max_speed_kmh, is_electrified, track_type) 
SELECT 
    'GZB-MB-001',
    (SELECT id FROM stations WHERE code = 'GZB'),
    (SELECT id FROM stations WHERE code = 'MB'),
    98.0, 110, true, 'double'
WHERE NOT EXISTS (SELECT 1 FROM tracks WHERE segment_id = 'GZB-MB-001');

-- Insert sample trains
INSERT INTO trains (train_number, train_name, train_type, priority, status) VALUES
('12004', 'Lucknow Shatabdi', 'express', 1, 'scheduled'),
('14006', 'Lichchavi Express', 'express', 2, 'scheduled'),
('15010', 'Gorakhpur Express', 'passenger', 3, 'scheduled')
ON CONFLICT (train_number) DO NOTHING;
