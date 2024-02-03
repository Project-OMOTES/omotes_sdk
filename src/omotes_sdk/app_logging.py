#  Copyright (c) 2023. Deltares & TNO
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Setup logging for this python application."""

import logging
import sys
from enum import Enum
from typing import Optional, Dict

CONFIGURED_LOGGERS: Dict[str, logging.Logger] = {}


class LogLevel(Enum):
    """Simple enum to cover log levels for logging library."""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR

    @staticmethod
    def parse(value: str) -> "LogLevel":
        """
        Parses a given string for LogLevel's.

        Parameters
        ----------
        value : str
                user provided string containing the requested log level

        Returns
        -------
        LogLevel
            Loglevel for this logger
        """
        lowered = value.lower()

        if lowered == "debug":
            result = LogLevel.DEBUG
        elif lowered == "info":
            result = LogLevel.INFO
        elif lowered in ["warning", "warn"]:
            result = LogLevel.WARNING
        elif lowered in ["err", "error"]:
            result = LogLevel.ERROR
        else:
            raise ValueError(f"Value {value} is not a valid log level.")

        return result


def setup_logging(log_level: LogLevel, logger_name: Optional[str]) -> logging.Logger:
    """
    Initializes logging.

    Parameters
    ----------
    log_level : LogLevel
        The LogLevel for this logger.
    logger_name : Optional[str]
        Name for this logger.
    """
    logger = logging.getLogger(logger_name)
    logger_name = logger_name if logger_name else ''

    if logger_name not in CONFIGURED_LOGGERS:
        print(f"Will use log level {log_level} for logger '{logger_name}'")
        logger.setLevel(log_level.value)

        log_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(threadName)s][%(filename)s:%(lineno)d]"
                "[%(levelname)s]: %(message)s"
        )
        log_handler.setFormatter(formatter)
        logger.addHandler(log_handler)
        CONFIGURED_LOGGERS[logger_name] = logger

    return logger
