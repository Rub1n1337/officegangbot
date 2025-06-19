# logs/logger.py
import logging
import sys

logger = logging.getLogger("BrawlStarsBot")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)

# Чтобы избежать дублирования логов, если логгер уже добавлен
if not logger.hasHandlers():
    logger.addHandler(handler)
