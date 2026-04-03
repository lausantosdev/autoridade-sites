"""
Logger — Logging estruturado para o SiteGen.

Substitui print() nos módulos core/ por logging com severidade e timestamp.
Os emojis são mantidos apenas no CLI (generate.py/server.py) para UX.
"""
import logging
import sys


def get_logger(name: str = "sitegen") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
