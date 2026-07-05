"""
db.py — asyncpg connection pool factory for the VALORANT Tournament Bot.
"""

import asyncpg
import config


async def create_pool() -> asyncpg.Pool:
    """Create and return a connection pool. Called once in setup_hook."""
    return await asyncpg.create_pool(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        min_size=1,
        max_size=10,
        command_timeout=30,
    )
