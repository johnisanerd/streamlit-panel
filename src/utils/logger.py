"""
Merkezi loglama modülü.
Konsola ve isteğe bağlı olarak dosyaya log yazar.
"""

import logging
import sys
from pathlib import Path
from src.utils.config import config


def get_logger(name: str) -> logging.Logger:
    """
    Belirtilen isimle yapılandırılmış bir logger döndürür.

    Args:
        name: Logger adı (genellikle __name__ kullanılır)

    Returns:
        Yapılandırılmış Logger nesnesi
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Konsol handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Dosya handler (log dizini varsa)
    log_path = Path(config.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
