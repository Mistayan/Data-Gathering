# -*- coding: utf-8 -*-
import os
from logging import config
from types import MappingProxyType
from typing import Final
import brotli

__version__ = (0, 1, 3)
del brotli.__version__
VERBOSITY_COUNT_TO_LEVEL: Final = MappingProxyType({
    0: "CRITICAL",
    1: "ERROR",
    2: "WARNING",
    3: "INFO",
    4: "DEBUG",
})
DEBUG: Final = VERBOSITY_COUNT_TO_LEVEL[4]  # prod config
log_config = {
    "version": 1,
    "root": {
        "handlers": ["console"],
        "level": DEBUG
    },
    'handlers': {
        'console': {
            'level': DEBUG,
            'class': 'logging.StreamHandler',
            'formatter': 'std_out',
        }
    },
    'loggers': {
        'myapp': {
            'handlers': ['console'],
            'level': DEBUG,
            'propagate': True if DEBUG == "DEBUG" else False
        },
    },
    "formatters": {
        "std_out": {
            "format": "%(levelname)s## %(asctime)s ##  %(module)s.%(funcName)s@%(lineno)d "
                      "==> :  %(message)s",
            "datefmt": "%d-%m %H:%M:%S"
        }
    },
}

config.dictConfig(log_config)
MAX_WORKERS = os.cpu_count() // 2 - 1
