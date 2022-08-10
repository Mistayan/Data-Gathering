# -*- coding: utf-8 -*-
import logging
from types import MappingProxyType
from typing import Final
import coloredlogs

__version__ = (0, 1, 3)
NUM_OF_THE_DAY = 2
VERBOSITY_COUNT_TO_LEVEL: Final = MappingProxyType({
    0: "CRITICAL",
    1: "ERROR",
    2: "WARNING",
    3: "INFO",
    4: "DEBUG",
})

DEBUG: Final = VERBOSITY_COUNT_TO_LEVEL[NUM_OF_THE_DAY]  # prod config
coloredlogs.install(DEBUG)
MAX_WORKERS = NUM_OF_THE_DAY
