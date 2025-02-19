from tortoise import Tortoise
import logging
import os

logger = logging.getLogger(__name__)

# Create a data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

TORTOISE_ORM_CONFIG = {
    "connections": {
        "default": "sqlite://data/db.sqlite3"
    },
    "apps": {
        "models": {
            "models": [
                "internal.repository.course",
                "internal.repository.student_progress",
                "aerich.models"
            ],
            "default_connection": "default"
        }
    }
}

async def init_db() -> None:
    """Initialize database connection and setup initial data.

    Raises:
        Exception: If database connection fails
    """
    try:
        # Initialize database connection
        await Tortoise.init(
            db_url="sqlite://data/db.sqlite3",
            modules={"models": [
                "internal.repository.course",
                "internal.repository.student_progress",
                "aerich.models"
            ]},
            timezone="UTC"
        )

        # Generate schemas for all models
        await Tortoise.generate_schemas()
        logger.info("Successfully created database schemas")

    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

async def close_db() -> None:
    """Close database connections."""
    await Tortoise.close_connections()
