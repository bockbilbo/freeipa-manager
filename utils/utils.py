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
import os
import socket

import yaml

from utils.ad_handler import ADHandler
from utils.cache_handler import CacheHandler
from utils.freeipa_handler import FreeIPAHandler
from utils.logger import Logger
from utils.menu import Menu
from utils.notifier import Notifier


class Utils:

    def __init__(self, config_file: str):

        self.log = logging.getLogger('freeipa_manager')

        self.config_file = config_file

        self.__load_settings(self.__load_config_file())

        self.logger = Logger(log_file=self.log_file,
                             log_level=self.log_level)

        self.cache_handler = CacheHandler(cache_files=self.cache_files,
                                          cache_validity=self.cache_validity)

        self.freeipa_handler = FreeIPAHandler(freeipa_credentials=self.freeipa_credentials,
                                              freeipa_gids=self.freeipa_gids,
                                              cache_handler=self.cache_handler,
                                              csv_files=self.csv_files,
                                              password_gracious_period=self.password_gracious_period)

        self.ad_handler = ADHandler(ad_settings=self.ad_settings,
                                    cache_handler=self.cache_handler,
                                    corporate_email_domains=self.corporate_email_domains)
        self.notifier = None

        self.menu = Menu(log_file=self.log_file,
                         cache_files=self.cache_files,
                         csv_files=self.csv_files,
                         freeipa_gids=self.freeipa_gids,
                         valid_sync_email_domains=self.valid_sync_email_domains,
                         cache_path=self.paths['cache'],
                         cache_validity=self.cache_validity,
                         password_gracious_period=self.password_gracious_period,
                         notification_days=self.notification_days,
                         )

    def __check_required_files(self) -> bool:

        return_value = True

        self.log.debug('Validating required files for program execution')

        if not os.path.isdir(self.paths['cache']):
            self.log.debug(f"Cache directory {self.paths['cache']} missing, created")
            os.mkdir(self.paths['cache'])

        for template in self.template_files:
            if not os.path.isfile(self.template_files[template]):
                self.log.debug(f'Missing required template file: {self.template_files[template]}')
                return_value = False

        if return_value:
            self.log.debug('Validation complete, everything is in order')
        else:
            self.log.debug('Validation complete, problems found')

        return return_value

    def __check_service_status(self, host: str, port: int) -> bool:

        self.log.debug(f'Starting TCP check to {host}:{port}')

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)

        try:
            s.connect((host, port))
            s.shutdown(socket.SHUT_RDWR)

            self.log.debug(f'TCP check to {host}:{port} successful')

            return True

        except (socket.timeout, ConnectionRefusedError):
            self.log.debug(f'TCP check to {host}:{port} unsuccessful')

            return False

        finally:
            s.close()

    def __diff_freeipa_ad_user(self, user_id: str) -> bool:

        ad_user = self.ad_handler.get_ad_user(user_id)
        freeipa_user = self.freeipa_handler.get_freeipa_user(user_id)

        return_value = {}

        if self.freeipa_handler.get_freeipa_users() and freeipa_user and ad_user and user_id:

            self.log.debug(f'Calculating differences between FreeIPA and AD records for user {user_id}')

            for key in freeipa_user:
                if key in ad_user and key not in self.ignore_keys_on_sync:

                    if ad_user[key] != freeipa_user[key]:

                        if key == 'manager':
                            if ad_user[key] in self.freeipa_handler.get_freeipa_users():
                                return_value[key] = ad_user[key]
                                self.log.debug(f'New value for {key} found: {ad_user[key]}')
                        else:
                            return_value[key] = ad_user[key]
                            self.log.debug(f'New value for {key} found: {ad_user[key]}')

            if return_value != {}:
                self.log.debug(f'All differences identified for user {user_id}')
            else:
                self.log.debug(f'No differences found for user {user_id}')

        else:
            self.log.warning('No valid data provided for difference calculation')

        return return_value

    def __get_terminated_users(self) -> list:

        self.log.debug('Obtaining list of terminated users')
        terminated_users = []

        for user in self.freeipa_handler.get_freeipa_users():
            if user not in self.ad_handler.get_ad_users() and self.__is_user_synchronizable(user):
                terminated_users.append(user)
                self.log.debug(f'User {user} has been terminated')

        if not terminated_users:
            self.log.debug('No terminated users found')
        else:
            self.log.debug('List of terminated users obtained')

        return terminated_users

    def __is_user_synchronizable(self, user_id: str) -> bool:

        self.log.debug(f'Identifying if user {user_id} can be synchronized with AD')

        user = self.freeipa_handler.get_freeipa_user(user_id)

        if user is not None:
            if self.is_email_valid(user['email']):
                self.log.debug('User should be in AD, can be synchronized')
                return True
            else:
                self.log.debug('User will not be in AD, cannot be synchronized')
                return False
        else:
            self.log.warning('No user given to evaluate synchronization')
            return False

    def __load_config_file(self) -> dict:

        settings = None

        try:
            self.log.info(f'Loading settings from config file {self.config_file}')
            with open(self.config_file, newline='') as yamlfile:
                settings = yaml.load(yamlfile, Loader=yaml.FullLoader)

        except (OSError, yaml.YAMLError) as e:
            self.log.error(f'Could not import configs from YAML file {self.config_file} due to an error: {e}')

        return settings

    def __load_settings(self, settings: dict) -> None:

        root_path = os.path.dirname(self.config_file)

        self.paths = {'main': root_path,
                      'cache': root_path+'/cache',
                      'templates': root_path+'/templates'}

        self.csv_files = {'import_template': 'import_template.csv',
                          'export_file': 'freeipa_user_export.csv',
                          'import_file': 'import_data.csv'}

        self.ad_settings = settings['ad_settings']

        self.freeipa_credentials = settings['freeipa_settings']['credentials']
        self.freeipa_gids = settings['freeipa_settings']['gids']

        self.ignore_keys_on_sync = settings['sync_settings']['ignore_keys_on_sync']
        self.corporate_email_domains = settings['sync_settings']['corporate_email_domains']
        self.valid_sync_email_domains = settings['sync_settings']['valid_sync_email_domains']

        self.smtp_relay_server = settings['notification_settings']['smtp_relay_server']
        self.from_email = settings['notification_settings']['from_email']
        self.password_gracious_period = settings['notification_settings']['password_gracious_period']
        self.notification_days = settings['notification_settings']['notification_days']
        self.template_files = settings['notification_settings']['templates']
        for file in self.template_files:
            self.template_files[file] = self.paths['templates'] + '/' + self.template_files[file]

        self.cache_validity = settings['cache_settings']['validity']
        self.cache_files = settings['cache_settings']['files']
        for file in self.cache_files:
            self.cache_files[file] = self.paths['cache'] + '/' + self.cache_files[file]

        self.log_level = settings['log_settings']['level']
        self.log_file = self.paths['main'] + '/' + settings['log_settings']['file']

    def __obtain_updated_user_data(self) -> dict:

        self.log.debug('Obtaining updated data from AD for all FreeIPA users')

        new_user_data = {}

        for user_id in self.freeipa_handler.get_freeipa_users():

            freeipa_user = self.freeipa_handler.get_freeipa_user(user_id)

            if self.is_email_valid(freeipa_user['email']):
                self.log.debug(f'Checking for new data for user {user_id}')

                user_diff = self.__diff_freeipa_ad_user(user_id)
                if user_diff != {}:
                    new_user_data[user_id] = user_diff

        self.log.debug('Updatable data obtained for all FreeIPA users')
        return new_user_data

    def check_server_connectivity(self) -> (bool, bool, bool):

        self.log.info('Testing AD, FreeIPA and SMTP server connectivity')

        ad_reachable = self.__check_service_status(self.ad_settings['credentials']['host'],
                                                   self.ad_settings['credentials']['port'])
        freeipa_reachable = self.__check_service_status(self.freeipa_credentials['host'], 443)

        smtp_reachable = self.__check_service_status(self.smtp_relay_server, 25)

        if ad_reachable and freeipa_reachable and smtp_reachable:
            self.log.info('Connectivity verified to AD, FreeIPA and SMTP servers')
        else:
            if not ad_reachable:
                self.log.warning('Could not connect to AD server during server connectivity check')
            if not freeipa_reachable:
                self.log.warning('Could not connect to FreeIPA server during server connectivity check')
            if not smtp_reachable:
                self.log.warning('Could not connect to SMTP server during server connectivity check')

        return ad_reachable, freeipa_reachable, smtp_reachable

    def delete_terminated_users(self) -> (list, list):

        self.log.info('Checking for terminated users')

        terminated_users = self.__get_terminated_users()

        deleted_users = []
        not_deleted_users = []

        for user_id in terminated_users:
            status = self.freeipa_handler.delete_freeipa_user(user_id)
            if status:
                self.log.info(f'User {user_id} deleted from FreeIPA')
                deleted_users.append(user_id)
            else:
                self.log.warning(f'User {user_id} not deleted from FreeIPA')
                not_deleted_users.append(user_id)

        if terminated_users:

            if deleted_users:
                self.log.debug('Updating FreeIPA cache')
                self.freeipa_handler.get_freeipa_users(force_update_cache=True)

            self.log.debug('Notifying admins of terminated user deletion')
            self.get_notifier().report_terminated(deleted_users, not_deleted_users)

            self.log.info('Terminated users were removed from FreeIPA')
            return deleted_users, not_deleted_users
        else:
            self.log.info('No terminated users found')
            return None, None

    def get_ad_handler(self) -> ADHandler:

        return self.ad_handler

    def get_cache_handler(self) -> CacheHandler:

        return self.cache_handler

    def get_csv_files(self) -> dict:

        return self.csv_files

    def get_freeipa_handler(self) -> FreeIPAHandler:

        return self.freeipa_handler

    def get_logger(self) -> Logger:

        return self.logger

    def get_menu(self) -> Menu:

        return self.menu

    def get_notifier(self) -> Notifier:

        if not self.notifier:
            self.notifier = Notifier(smtp_relay_server=self.smtp_relay_server,
                                     from_email=self.from_email,
                                     admin_emails=self.freeipa_handler.get_freeipa_admin_emails(),
                                     template_files=self.template_files,
                                     password_gracious_period=self.password_gracious_period)
        return self.notifier

    def get_password_gracious_period(self) -> int:
        return self.password_gracious_period

    def import_csv(self, file: str) -> (dict, list, list, list):

        imported_users, updated_users, skipped_users, not_imported_users = self.freeipa_handler.import_from_csv(file)

        if imported_users:
            self.log.info('Notifying new users of their accounts via email')

        for user_id in imported_users:
            password = imported_users[user_id]

            if password:
                user = self.freeipa_handler.get_freeipa_user(user_id)
                alias = user['alias'][0]
                name = user['name']
                email = user['email']

                self.log.debug(f'Sending new account notification to user {user_id}')

                status = self.get_notifier().notify_new_account(user_id, alias, name, email, password)

                if status:
                    self.log.info('New account notification sent')
                else:
                    self.log.warning('Problem found when sending the new account notification, email not sent')

        return imported_users, updated_users, skipped_users, not_imported_users

    def is_email_valid(self, email: str) -> bool:

        for domain in self.valid_sync_email_domains:
            if f'@{domain}' in email:
                self.log.debug(f'Email domain in {email} valid for synchronization')
                return True

        self.log.debug(f'Email domain in {email} not valid for synchronization')
        return False

    def process_password_expirations(self) -> (list, list, list):

        self.log.info('Processing pending password expiration notifications')

        notification_history = self.cache_handler.get_notification_history_cache()
        disabled_expired_users = self.cache_handler.get_disabled_expired_users_cache()

        update_cache = False

        notified_users = []
        expired_users = []
        new_disabled_expired_users = []
        new_notification_history = {}

        freeipa_users = self.freeipa_handler.get_freeipa_users()

        for user in freeipa_users:

            user_notifications = []

            if user in notification_history:
                user_notifications = notification_history[user]

            delta, exp_date = self.freeipa_handler.get_user_passwd_expiration(user)

            if delta <= max(self.notification_days):
                update_cache = True

            if 0 <= delta <= max(self.notification_days):
                if user_notifications:
                    new_notification_history[user] = user_notifications
                else:
                    new_notification_history[user] = []

            elif -self.password_gracious_period <= delta < 0:
                expired_users.append(user)
                self.log.debug(f'Password for user {user} is expired or has not been changed by the user after a reset')

            elif delta < -self.password_gracious_period:
                new_disabled_expired_users.append(user)

                if user not in disabled_expired_users:
                    self.freeipa_handler.disable_freeipa_user(user)
                    self.log.warning(f'Password for user {user} expired or not changed over the gracious period, '
                                     f'user disabled')

            if delta == 359 and delta not in user_notifications:

                self.log.debug(f'Notifying {user} about upcoming expiration')

                self.get_notifier().notify_expiration(user,
                                                      freeipa_users[user]['email'],
                                                      freeipa_users[user]['name'],
                                                      delta,
                                                      exp_date)
                notified_users.append(user)

                self.log.debug(f'Updating notification history cache for user {user}')
                new_notification_history[user].append(delta)

        if update_cache:
            if new_notification_history:
                self.log.debug('Updating password expiration notification history cache file')
                self.cache_handler.save_cache(notification_history=new_notification_history)

            if new_disabled_expired_users:
                self.log.debug('Updating disabled expired users cache file')
                self.cache_handler.save_cache(disabled_expired_users=new_disabled_expired_users)

        else:
            self.log.info('No password expiring in the next 2 weeks')

        if expired_users or new_disabled_expired_users:
            self.log.info('Notifying admins of password expirations')
            self.get_notifier().report_expirations(expired_users, new_disabled_expired_users)

        return notified_users, expired_users, new_disabled_expired_users

    def remind_password_change(self) -> (bool, list):

        self.log.info('Processing password change reminders')

        users_no_password = self.freeipa_handler.get_users_no_password()

        for user_id in users_no_password:
            self.log.debug(f'Reminding user {user_id} to reset its password')
            user = self.freeipa_handler.get_freeipa_user(user_id)
            self.get_notifier().remind_password_reset(user_id, alias=user['alias'][0], name=user['name'],
                                                      email=user['email'])

        if users_no_password:
            return True, users_no_password
        else:
            self.log.debug('No users to remind of expiring passwords at this time')
            return False, []

    def reset_user_password(self, user_id: str) -> (bool, str):

        password = self.freeipa_handler.reset_user_password(user_id)

        if password:
            user = self.freeipa_handler.get_freeipa_user(user_id)

            alias = ''
            if user['alias']:
                alias = user['alias'][0]

            name = user['name']
            email = user['email']

            self.log.debug(f'Sending password reset notification to user {user_id}')

            return self.get_notifier().notify_password_reset(user_id, alias, name, email, password), password
        else:
            self.log.error(f'Could not reset password for user {user_id}')
            return False, None

    def update_user_data_from_ad(self) -> (list, list):

        self.log.info('Starting user data synchronization from AD')

        updates_success = []
        updates_unsuccessful = []

        updated_user_data = self.__obtain_updated_user_data()

        for user in updated_user_data:

            if self.__is_user_synchronizable(user):
                self.log.debug(f'Updating user {user}')

                update_status = self.freeipa_handler.update_freeipa_user(user_id=user, **updated_user_data[user],
                                                                         update_cache=False)
                if update_status:
                    self.log.debug('The following fields were updated successfully:')
                    for key in updated_user_data[user]:
                        self.log.debug(f' - {key}: {updated_user_data[user][key]}')

                    updates_success.append(user)

                else:
                    updates_unsuccessful.append(user)
                    self.log.warning(f'User {user} could not be updated')

        if updated_user_data:
            self.log.info('Data synchronization from AD completed')

            if updates_success:
                self.log.info('Notifying admins about synchronized users')
                self.get_notifier().report_ad_updates(updates_success)

            self.log.debug('Updating FreeIPA cache')
            self.freeipa_handler.get_freeipa_users(force_update_cache=True)

        else:
            self.log.info('There is no data to synchronize from AD at this time')

        return updates_success, updates_unsuccessful

    def validate_running_environment(self, manual_server_check: bool) -> bool:

        if not self.__check_required_files():
            self.log.error('The program is missing required files to run and cannot be executed')
            return False

        else:
            if manual_server_check is False:
                ad_reachable, freeipa_reachable, smtp_reachable = self.check_server_connectivity()
                if not (ad_reachable == freeipa_reachable == smtp_reachable is True):
                    self.log.error('The program cannot connect to one or more servers required to run and cannot be '
                                   'executed')
                    return False
                else:
                    self.log.info('Running environment validated, all required files and servers available')
                    return True
            else:
                self.log.info('Program files validated, skipping server validation for manual server check request')
                return True
