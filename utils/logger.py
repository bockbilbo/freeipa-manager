# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2021  Unai Goikoetxeta

import logging


class Logger:

    def __init__(self, log_file: str, log_level: int = logging.WARNING):
        self.log = logging.getLogger('freeipa_manager')

        self.log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt='%Y-%m-%d %H:%M:%S')

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(self.log_formatter)
        self.log.addHandler(file_handler)
        self.log.setLevel(log_level)

    def enable_verbose(self) -> None:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self.log_formatter)
        self.log.addHandler(console_handler)
        self.log.info('Logging verbose enabled')

    def set_level_debug(self) -> None:
        self.log.setLevel(logging.DEBUG)
        self.log.info('Debug logging level enabled')

    def set_level_info(self) -> None:
        self.log.setLevel(logging.INFO)
        self.log.info('Info logging level enabled')
