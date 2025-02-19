from tortoise import Tortoise
import logging

logger = logging.getLogger(__name__)


TORTOISE_ORM_CONFIG = {
    "connections": {
        "default": "postgres://localhost:5432/postgres"
    },
    "apps": {
        "models": {
            "models": ["internal.repository.course", "aerich.models"],
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
            db_url=f"postgres://localhost:5432/postgres",
            modules={"models": ["internal.repository.course", "aerich.models"]},
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
