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

import datetime
import json
import logging
import os


class CacheHandler:

    def __init__(self, cache_files: dict,  cache_validity: int = 60):
        self.log = logging.getLogger('freeipa_manager')
        self.cache_files = cache_files
        self.cache_validity = cache_validity

        self.ad_cache = None
        self.freeipa_cache = None
        self.notification_history_cache = None
        self.disabled_users_cache = None

    def __check_file_validity(self, file: str) -> bool:
        stat = os.stat(file)
        file_time = datetime.datetime.fromtimestamp(stat.st_mtime)
        now = datetime.datetime.now()

        if now - datetime.timedelta(minutes=self.cache_validity) > file_time:
            self.log.debug(f'Cache file {file} is older than {self.cache_validity} minutes')
            return False
        else:
            self.log.debug(f'Cache file {file} is newer than {self.cache_validity} minutes')
            return True

    def __load_json_file(self, file_path: str) -> bool:
        self.log.debug(f'Loading JSON file {file_path}')

        try:
            with open(file_path, 'r') as fp:
                cache_data = json.load(fp)
                self.log.debug(f'JSON file loaded successfully')
                return cache_data

        except json.decoder.JSONDecodeError:
            self.log.error(f'JSON file {file_path} could not be loaded')
            return None

    def __save_json_file(self, file_path: str, data: {dict, list}) -> bool:
        self.log.debug(f'Saving JSON file {file_path}')

        try:
            with open(file_path, 'w') as fp:
                json.dump(data, fp)

            self.log.debug(f'JSON saved successfully')

            return True

        except json.decoder.JSONDecodeError:
            self.log.error(f'JSON file {file_path} could not be saved')
            return False

    def delete_cache(self) -> bool:
        self.log.debug('Deleting FreeIPA and AD cache files')

        return_value = False

        if os.path.exists(self.cache_files['ad_cache']):
            os.remove(self.cache_files['ad_cache'])
            self.log.debug('AD cache file deleted')
            return_value = True

        if os.path.exists(self.cache_files['freeipa_cache']):
            os.remove(self.cache_files['freeipa_cache'])
            self.log.debug('FreeIPA cache file deleted')
            return_value = True

        if not return_value:
            self.log.warning('FreeIPA and AD cache files cannot be deleted because they do not exist')

        return return_value

    def get_ad_cache(self) -> dict:
        self.log.debug('Retrieving AD cache')

        if not self.is_cache_outdated('ad_cache'):

            if self.ad_cache:
                self.log.debug('Retrieving cache from memory')
                return self.ad_cache
            else:
                self.log.debug('Retrieving cache from json file')
                self.ad_cache = self.__load_json_file(self.cache_files['ad_cache'])
                return self.ad_cache
        else:
            self.log.debug('Cache outdated, cannot be retrieved')
            return None

    def get_disabled_expired_users_cache(self) -> list:
        self.log.debug('Retrieving disabled expired users cache')

        if self.disabled_users_cache:
            self.log.debug('Retrieving cache from memory')
            return self.disabled_users_cache
        else:
            if os.path.exists(self.cache_files['disabled_users_cache']):
                self.log.debug('Retrieving cache from json file')
                self.disabled_users_cache = \
                    self.__load_json_file(self.cache_files['disabled_users_cache'])
                return self.disabled_users_cache
            else:
                self.log.debug('No cache available, creating new one')
                self.disabled_users_cache = []
                return self.disabled_users_cache

    def get_freeipa_cache(self) -> dict:
        self.log.debug('Retrieving FreeIPA cache')

        if not self.is_cache_outdated('freeipa_cache'):
            if self.freeipa_cache:
                self.log.debug('Retrieving cache from memory')
                return self.freeipa_cache
            else:
                self.log.debug('Retrieving cache from json file')
                self.freeipa_cache = self.__load_json_file(self.cache_files['freeipa_cache'])
                return self.freeipa_cache
        else:
            self.log.debug('Cache outdated, cannot be retrieved')
            return None

    def get_notification_history_cache(self) -> dict:
        self.log.debug('Retrieving notification history cache')

        if self.notification_history_cache:
            self.log.debug('Retrieving cache from memory')
            return self.notification_history_cache
        else:
            if os.path.exists(self.cache_files['notification_history_cache']):
                self.log.debug('Retrieving cache from json file')
                self.notification_history_cache = \
                    self.__load_json_file(self.cache_files['notification_history_cache'])
                return self.notification_history_cache
            else:
                self.log.debug('No cache available, creating new one')
                self.notification_history_cache = {}
                return self.notification_history_cache

    def is_cache_outdated(self, cache_file: str = None) -> bool:
        self.log.debug(f'Verifying if cache is valid')

        if not cache_file:

            for file in self.cache_files:
                if file != 'notification_history_cache' and file!= 'disabled_users_cache':
                    if os.path.exists(self.cache_files[file]):

                        file_valid = self.__check_file_validity(self.cache_files[file])
                        if not file_valid:
                            return True

                    else:
                        self.log.warning(f'Cache file {self.cache_files[file]} does not exist')
                        return True

        else:
            self.log.debug(f'Performing validation for cache file {cache_file}')

            if cache_file != 'notification_history_cache' and cache_file != 'disabled_users_cache':
                if os.path.exists(self.cache_files[cache_file]):

                    file_valid = self.__check_file_validity(self.cache_files[cache_file])
                    if not file_valid:
                        return True
                else:
                    self.log.warning(f'Cache file {self.cache_files[cache_file]} does not exist')
                    return True

        return False

    def save_cache(self, ad_users: dict = None,
                   freeipa_users: dict = None,
                   notification_history: dict = None,
                   disabled_expired_users: list = None) -> bool:
        return_value = []

        if ad_users:
            self.log.info('Saving AD cache')

            cache_updated = self.__save_json_file(self.cache_files['ad_cache'], ad_users)
            if cache_updated:
                self.ad_cache = ad_users

            return_value.append(cache_updated)

        if freeipa_users:
            self.log.info('Saving FreeIPA cache')

            cache_updated = self.__save_json_file(self.cache_files['freeipa_cache'], freeipa_users)

            if cache_updated:
                self.freeipa_cache = freeipa_users

            return_value.append(cache_updated)

        if notification_history:
            self.log.info('Saving notification history cache')

            cache_updated = self.__save_json_file(self.cache_files['notification_history_cache'], notification_history)

            if cache_updated:
                self.notification_history_cache = notification_history

            return_value.append(cache_updated)

        if disabled_expired_users:
            self.log.info('Saving expired users cache')

            cache_updated = self.__save_json_file(self.cache_files['disabled_users_cache'], disabled_expired_users)

            if cache_updated:
                self.disabled_users_cache = disabled_expired_users

            return_value.append(cache_updated)

        if False in return_value:
            return False
        elif not return_value:
            return False
        else:
            return True
