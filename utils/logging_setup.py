"""
Logging configuration using loguru
Sets up structured logging for the entire application
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logging(config: dict) -> None:
    """
    Configure loguru logging

    Args:
        config: Logging configuration dictionary
    """
    # Remove default handler
    logger.remove()

    # Get config
    log_level = config['logging']['level']
    log_file = config['logging']['log_file']
    max_size = config['logging']['max_log_size_mb'] * 1024 * 1024  # Convert to bytes
    backup_count = config['logging']['backup_count']

    # Console handler (colored, formatted)
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )

    # File handler (rotation and retention)
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        rotation=max_size,
        retention=backup_count,
        compression="zip"
    )

    logger.info(f"Logging initialized: level={log_level}, file={log_file}")


if __name__ == "__main__":
    """Test logging setup"""
    import yaml

    # Load config
    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    setup_logging(config)

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
