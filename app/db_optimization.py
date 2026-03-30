from sqlalchemy import text
from app.database import engine
from app.logging_config import logger
import asyncio

async def create_indexes():
    """Create database indexes for better performance"""
    indexes = [
        # Faculty table indexes
        "CREATE INDEX IF NOT EXISTS idx_faculty_name ON api.faculty (fname, lname);",
        "CREATE INDEX IF NOT EXISTS idx_faculty_name_en ON api.faculty (fname_en, lname_en);",
        "CREATE INDEX IF NOT EXISTS idx_faculty_position ON api.faculty (position);",
        "CREATE INDEX IF NOT EXISTS idx_faculty_email ON api.faculty (email);",
        "CREATE INDEX IF NOT EXISTS idx_faculty_updated_at ON api.faculty (updated_at);",
        "CREATE INDEX IF NOT EXISTS idx_faculty_is_expert ON api.faculty (is_expert);",
        
        # News and Activity indexes
        "CREATE INDEX IF NOT EXISTS idx_news_created_at ON news (created_at);",
        "CREATE INDEX IF NOT EXISTS idx_news_category ON news (category);",
        "CREATE INDEX IF NOT EXISTS idx_activities_created_at ON activities (created_at);",
        
        # Page indexes
        "CREATE INDEX IF NOT EXISTS idx_pages_slug ON pages (slug);",
        "CREATE INDEX IF NOT EXISTS idx_pages_is_published ON pages (is_published);",
        "CREATE INDEX IF NOT EXISTS idx_pages_updated_at ON pages (updated_at);",
        
        # Appeal indexes
        "CREATE INDEX IF NOT EXISTS idx_appeals_status ON appeals (status);",
        "CREATE INDEX IF NOT EXISTS idx_appeals_created_at ON appeals (created_at);",
        
        # Staff indexes
        "CREATE INDEX IF NOT EXISTS idx_staff_type ON staff (type);",
        "CREATE INDEX IF NOT EXISTS idx_staff_order_index ON staff (order_index);",
        
        # Banner, Mission, Course, Award indexes
        "CREATE INDEX IF NOT EXISTS idx_banners_is_active ON api.banners (is_active);",
        "CREATE INDEX IF NOT EXISTS idx_banners_order_index ON api.banners (order_index);",
        "CREATE INDEX IF NOT EXISTS idx_missions_order_index ON api.missions (order_index);",
        "CREATE INDEX IF NOT EXISTS idx_courses_order_index ON api.courses (order_index);",
        "CREATE INDEX IF NOT EXISTS idx_awards_order_index ON api.awards (order_index);",
        "CREATE INDEX IF NOT EXISTS idx_statistics_order_index ON api.statistics (order_index);",
        "CREATE INDEX IF NOT EXISTS idx_contact_info_order_index ON api.contact_info (order_index);",
    ]
    
    try:
        async with engine.begin() as conn:
            for index_sql in indexes:
                await conn.execute(text(index_sql))
                logger.info(f"Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
        
        logger.info("All database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating database indexes: {e}")
        raise

async def analyze_query_performance():
    """Analyze and log slow queries"""
    try:
        async with engine.begin() as conn:
            # Enable query logging if needed
            await conn.execute(text("SET log_min_duration_statement = 1000;"))  # Log queries > 1s
            logger.info("Query performance monitoring enabled")
            
    except Exception as e:
        logger.error(f"Error setting up query performance monitoring: {e}")

if __name__ == "__main__":
    asyncio.run(create_indexes())
