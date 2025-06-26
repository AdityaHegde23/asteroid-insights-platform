-- Asteroid Insights Platform Database Schema
-- This schema supports the ETL pipeline from NASA API to Azure SQL Database
-- Calculations and processing happen in Python ETL code, not in SQL


-- Raw asteroid data table (exactly as received from NASA API)
CREATE TABLE raw_asteroid_data (
    id BIGINT PRIMARY KEY,                           -- NASA asteroid ID
    name NVARCHAR(255) NOT NULL,                     -- Asteroid name/designation
    nasa_jpl_url NVARCHAR(500),                      -- NASA JPL URL
    absolute_magnitude_h DECIMAL(5,2),               -- Absolute magnitude
    estimated_diameter_min_km DECIMAL(10,6),         -- Minimum estimated diameter
    estimated_diameter_max_km DECIMAL(10,6),         -- Maximum estimated diameter
    is_potentially_hazardous_asteroid BIT,           -- Hazardous flag
    is_sentry_object BIT,                            -- Sentry object flag
    close_approach_date DATE,                        -- Close approach date
    close_approach_full NVARCHAR(50),                -- Full close approach string
    epoch_osculation DECIMAL(15,6),                  -- Epoch of osculation
    eccentricity DECIMAL(10,6),                      -- Orbital eccentricity
    semi_major_axis DECIMAL(15,6),                   -- Semi-major axis
    inclination DECIMAL(10,6),                       -- Orbital inclination
    ascending_node_longitude DECIMAL(10,6),          -- Longitude of ascending node
    orbital_period DECIMAL(15,6),                    -- Orbital period
    perihelion_distance DECIMAL(15,6),               -- Perihelion distance
    perihelion_argument DECIMAL(10,6),               -- Argument of perihelion
    aphelion_distance DECIMAL(15,6),                 -- Aphelion distance
    perihelion_time DECIMAL(15,6),                   -- Perihelion time
    mean_anomaly DECIMAL(10,6),                      -- Mean anomaly
    mean_motion DECIMAL(15,6),                       -- Mean motion
    equinox NVARCHAR(10),                            -- Equinox
    orbit_determination_date DATE,                   -- Orbit determination date
    orbit_uncertainty NVARCHAR(10),                  -- Orbit uncertainty
    minimum_orbit_intersection DECIMAL(15,6),        -- Minimum orbit intersection
    jupiter_tisserand_invariant DECIMAL(10,6),       -- Jupiter Tisserand invariant
    earth_minimum_orbit_intersection_distance DECIMAL(15,6), -- Earth MOID
    orbit_id NVARCHAR(20),                           -- Orbit ID
    object_designation NVARCHAR(50),                 -- Object designation
    close_approach_epoch_unix BIGINT,                -- Close approach epoch (Unix)
    relative_velocity_km_per_sec DECIMAL(15,6),      -- Relative velocity (km/s)
    relative_velocity_km_per_hour DECIMAL(15,6),     -- Relative velocity (km/h)
    relative_velocity_miles_per_hour DECIMAL(15,6),  -- Relative velocity (mph)
    miss_distance_astronomical DECIMAL(15,6),        -- Miss distance (AU)
    miss_distance_lunar DECIMAL(15,6),               -- Miss distance (lunar)
    miss_distance_kilometers DECIMAL(15,6),          -- Miss distance (km)
    orbiting_body NVARCHAR(50),                      -- Orbiting body
    nasa_data_json NVARCHAR(MAX),                    -- Complete NASA JSON response
    fetched_at DATETIME2 DEFAULT GETUTCDATE(),        -- When data was fetched
    created_at DATETIME2 DEFAULT GETUTCDATE(),        -- Record creation timestamp
    updated_at DATETIME2 DEFAULT GETUTCDATE()         -- Record update timestamp
);
GO

-- Processed asteroid insights table (calculated data from Python ETL)
CREATE TABLE processed_asteroid_insights (
    id BIGINT PRIMARY KEY IDENTITY(1,1),             -- Auto-generated ID
    raw_asteroid_id BIGINT NOT NULL,                 -- Reference to raw data
    name NVARCHAR(255) NOT NULL,                     -- Asteroid name
    risk_score DECIMAL(5,4),                         -- Calculated risk score (0-1) from Python
    hazard_level NVARCHAR(20),                       -- HIGH/MEDIUM/LOW from Python
    size_category NVARCHAR(50),                      -- Small/Medium/Large from Python
    orbit_type NVARCHAR(50),                         -- Nearly Circular/Low Eccentricity/High Eccentricity from Python
    inclination_type NVARCHAR(50),                   -- Low/Medium/High Inclination from Python
    velocity_category NVARCHAR(50),                  -- Slow/Medium/Fast from Python
    distance_category NVARCHAR(50),                  -- Very Close/Close/Moderate/Far from Python
    days_to_approach INT,                            -- Days until close approach from Python
    is_high_priority BIT,                            -- High priority for monitoring from Python
    threat_level NVARCHAR(20),                       -- CRITICAL/HIGH/MEDIUM/LOW from Python
    recommended_action NVARCHAR(255),                -- Recommended monitoring action from Python
    orbital_insights NVARCHAR(MAX),                  -- JSON with orbital insights from Python
    size_insights NVARCHAR(MAX),                     -- JSON with size insights from Python
    velocity_insights NVARCHAR(MAX),                 -- JSON with velocity insights from Python
    distance_insights NVARCHAR(MAX),                 -- JSON with distance insights from Python
    processing_metadata NVARCHAR(MAX),               -- JSON with processing metadata from Python
    processed_at DATETIME2 DEFAULT GETUTCDATE(),      -- When processing occurred
    created_at DATETIME2 DEFAULT GETUTCDATE(),        -- Record creation timestamp
    updated_at DATETIME2 DEFAULT GETUTCDATE(),        -- Record update timestamp
    
    -- Foreign key constraint
    CONSTRAINT FK_processed_raw FOREIGN KEY (raw_asteroid_id) 
        REFERENCES raw_asteroid_data(id)
);
GO

-- Indexes for better query performance
CREATE INDEX IX_raw_asteroid_data_name ON raw_asteroid_data(name);
CREATE INDEX IX_raw_asteroid_data_hazardous ON raw_asteroid_data(is_potentially_hazardous_asteroid);
CREATE INDEX IX_raw_asteroid_data_approach_date ON raw_asteroid_data(close_approach_date);
CREATE INDEX IX_raw_asteroid_data_fetched_at ON raw_asteroid_data(fetched_at);

CREATE INDEX IX_processed_risk_score ON processed_asteroid_insights(risk_score);
CREATE INDEX IX_processed_hazard_level ON processed_asteroid_insights(hazard_level);
CREATE INDEX IX_processed_threat_level ON processed_asteroid_insights(threat_level);
CREATE INDEX IX_processed_processed_at ON processed_asteroid_insights(processed_at);
CREATE INDEX IX_processed_raw_asteroid_id ON processed_asteroid_insights(raw_asteroid_id);
GO

-- Views for common queries (read-only analytics)
CREATE VIEW v_hazardous_asteroids AS
SELECT 
    r.id,
    r.name,
    r.is_potentially_hazardous_asteroid,
    r.close_approach_date,
    r.miss_distance_kilometers,
    r.relative_velocity_km_per_hour,
    p.risk_score,
    p.hazard_level,
    p.threat_level,
    p.recommended_action
FROM raw_asteroid_data r
LEFT JOIN processed_asteroid_insights p ON r.id = p.raw_asteroid_id
WHERE r.is_potentially_hazardous_asteroid = 1;
GO

CREATE VIEW v_high_risk_asteroids AS
SELECT 
    r.id,
    r.name,
    r.close_approach_date,
    r.miss_distance_kilometers,
    r.relative_velocity_km_per_hour,
    p.risk_score,
    p.hazard_level,
    p.size_category,
    p.orbit_type,
    p.days_to_approach
FROM raw_asteroid_data r
INNER JOIN processed_asteroid_insights p ON r.id = p.raw_asteroid_id
WHERE p.risk_score >= 0.7;
GO

CREATE VIEW v_asteroid_summary AS
SELECT 
    COUNT(*) as total_asteroids,
    SUM(CASE WHEN is_potentially_hazardous_asteroid = 1 THEN 1 ELSE 0 END) as hazardous_count,
    SUM(CASE WHEN is_sentry_object = 1 THEN 1 ELSE 0 END) as sentry_count,
    AVG(CAST(estimated_diameter_max_km AS FLOAT)) as avg_diameter_km,
    MIN(close_approach_date) as earliest_approach,
    MAX(close_approach_date) as latest_approach
FROM raw_asteroid_data;
GO

-- Simple stored procedure for getting asteroid data (no calculations)
CREATE PROCEDURE sp_GetAsteroidData
    @AsteroidId BIGINT
AS
BEGIN
    SELECT 
        r.*,
        p.risk_score,
        p.hazard_level,
        p.threat_level,
        p.recommended_action,
        p.orbital_insights,
        p.size_insights,
        p.velocity_insights,
        p.distance_insights
    FROM raw_asteroid_data r
    LEFT JOIN processed_asteroid_insights p ON r.id = p.raw_asteroid_id
    WHERE r.id = @AsteroidId;
END
GO

-- Insert sample data for testing (optional)
-- This can be removed in production
INSERT INTO raw_asteroid_data (
    id, name, nasa_jpl_url, absolute_magnitude_h, 
    estimated_diameter_min_km, estimated_diameter_max_km,
    is_potentially_hazardous_asteroid, is_sentry_object,
    close_approach_date, miss_distance_kilometers,
    relative_velocity_km_per_hour, fetched_at
) VALUES 
(2000433, '433 Eros', 'http://ssd.jpl.nasa.gov/sbdb.cgi?sstr=2000433', 11.16, 
 0.15, 0.34, 0, 0, '2024-01-15', 50000000, 25000, GETUTCDATE()),
(2001862, '1862 Apollo', 'http://ssd.jpl.nasa.gov/sbdb.cgi?sstr=2001862', 16.25, 
 0.08, 0.18, 1, 1, '2024-02-20', 2500000, 45000, GETUTCDATE());
GO

-- Grant permissions (adjust as needed for your Azure SQL setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON raw_asteroid_data TO [your-app-user];
-- GRANT SELECT, INSERT, UPDATE, DELETE ON processed_asteroid_insights TO [your-app-user];
-- GRANT EXECUTE ON sp_GetAsteroidData TO [your-app-user];
GO

PRINT 'Asteroid Insights Database Schema created successfully!';
PRINT 'Tables: raw_asteroid_data, processed_asteroid_insights';
PRINT 'Views: v_hazardous_asteroids, v_high_risk_asteroids, v_asteroid_summary';
PRINT 'Stored Procedure: sp_GetAsteroidData';
PRINT 'All calculations and processing will be done in Python ETL code.';
GO 