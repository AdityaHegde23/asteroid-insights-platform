-- Migration script to add unique constraint to processed_asteroid_insights table
-- This ensures no duplicate processed insights for the same asteroid

-- Check if the constraint already exists
IF NOT EXISTS (
    SELECT * FROM sys.objects 
    WHERE object_id = OBJECT_ID(N'[dbo].[UQ_processed_raw_asteroid_id]') 
    AND type in (N'UQ')
)
BEGIN
    -- Add unique constraint to prevent duplicate processed insights
    ALTER TABLE processed_asteroid_insights 
    ADD CONSTRAINT UQ_processed_raw_asteroid_id UNIQUE (raw_asteroid_id);
    
    PRINT 'Successfully added unique constraint UQ_processed_raw_asteroid_id to processed_asteroid_insights table';
END
ELSE
BEGIN
    PRINT 'Unique constraint UQ_processed_raw_asteroid_id already exists on processed_asteroid_insights table';
END
GO

-- Verify the constraint was added
SELECT 
    tc.CONSTRAINT_NAME,
    tc.TABLE_NAME,
    tc.CONSTRAINT_TYPE
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
WHERE tc.TABLE_NAME = 'processed_asteroid_insights' 
    AND tc.CONSTRAINT_NAME = 'UQ_processed_raw_asteroid_id';
GO

PRINT 'Migration completed successfully!';
PRINT 'The processed_asteroid_insights table now prevents duplicate insights for the same asteroid.';
GO 