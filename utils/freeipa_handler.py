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

import csv
import datetime
import logging
import os
import secrets
import string

import python_freeipa
from python_freeipa import exceptions as freeipa_exceptions
from requests.exceptions import ConnectionError
from urllib3.exceptions import NewConnectionError
from urllib3.exceptions import TimeoutError

from utils.cache_handler import CacheHandler


class FreeIPAHandler:

    def __init__(self, freeipa_credentials: dict, freeipa_gids: dict, cache_handler: CacheHandler, csv_files: dict,
                 password_gracious_period: int):
        self.log = logging.getLogger('freeipa_manager')
        self.freeipa_credentials = freeipa_credentials
        self.cache_handler = cache_handler
        self.freeipa_gids = freeipa_gids
        self.csv_files = csv_files
        self.password_gracious_period = password_gracious_period
        self.freeipa_connection = self.__connect_to_freeipa()

    def __connect_to_freeipa(self) -> python_freeipa.ClientMeta:
        self.log.debug('Connecting to FreeIPA server')

        try:
            freeipa_client = python_freeipa.ClientMeta(self.freeipa_credentials['host'])

            freeipa_client.login(self.freeipa_credentials['username'], self.freeipa_credentials['password'])

            self.log.debug('Connection established')

            return freeipa_client

        except (TimeoutError,
                NewConnectionError,
                ConnectionError,
                freeipa_exceptions.BadRequest,
                freeipa_exceptions.Denied,
                freeipa_exceptions.FreeIPAError,
                freeipa_exceptions.NotFound,
                freeipa_exceptions.Unauthorized,
                freeipa_exceptions.UserLocked) as e:

            self.log.error(f"Could not connect to FreeIPA server {self.freeipa_credentials['host']}: {e}")
            return None

    def __is_user_preserved(self, user_id: str) -> bool:
        self.log.debug(f'Checking if user {user_id} account is preserved')

        try:
            query_data = self.freeipa_connection.user_find(o_uid=user_id, o_preserved="True")

            if query_data['result']:
                self.log.debug(f'Account {user_id} is preserved')
                return True
            else:
                self.log.debug(f'Account {user_id} is not preserved')
                return False

        except (freeipa_exceptions.BadRequest,
                freeipa_exceptions.Denied,
                freeipa_exceptions.FreeIPAError,
                freeipa_exceptions.NotFound,
                freeipa_exceptions.Unauthorized,
                freeipa_exceptions.UserLocked) as e:

            self.log.error(f'Could not check if user is preserved due to a problem with the FreeIPA server: {e}')
            return None

    def __generate_alias(self, name: str, lastname: str) -> str:
        self.log.debug(f'Generating user alias for {name} {lastname}')

        alias = name[:1].lower() + lastname.lower()

        valid_alias = False
        counter = 1

        while valid_alias is False:

            query_data = self.freeipa_connection.user_find(o_krbprincipalname=alias)

            if query_data['count'] == 0:
                valid_alias = True
            else:
                alias = alias + str(counter)
                counter += 1

        self.log.debug(f'Alias for user will be {alias}')

        return alias

    def __generate_password(self, length=15) -> str:
        self.log.debug(f'Generating random password')

        chars = string.ascii_letters + string.digits + '!@#%&$?'
        new_password = ''.join(secrets.choice(chars) for _ in range(length))

        return new_password

    @staticmethod
    def __get_user_data(user) -> dict:
        user_data = {'email': '', 'alias': '', 'full_name': '', 'name': '', 'lastname': '', 'job_title': '',
                     'street_address': '', 'city': '', 'state': '', 'zip_code': '', 'org_unit': '',
                     'employee_number': '', 'employee_type': '', 'preferred_language': '', 'phone_number': '',
                     'manager': '', 'member_of': '', 'krbpasswordexpiration': '', 'krblastpwdchange': ''}

        if 'mail' in user:
            user_data['email'] = user['mail'][0]
        if 'krbprincipalname' in user and len(user['krbprincipalname']) > 1:
            alias = []
            for i in range(1, len(user['krbprincipalname'])):
                alias.append(user['krbprincipalname'][i][:user['krbprincipalname'][i].index('@')])
            user_data['alias'] = alias
        if 'cn' in user:
            user_data['full_name'] = user['cn'][0]
        if 'givenname' in user:
            user_data['name'] = user['givenname'][0]
        if 'sn' in user:
            user_data['lastname'] = user['sn'][0]
        if 'title' in user:
            user_data['job_title'] = user['title'][0]
        if 'street' in user:
            user_data['street_address'] = user['street'][0]
        if 'l' in user:
            user_data['city'] = user['l'][0]
        if 'st' in user:
            user_data['state'] = user['st'][0]
        if 'postalcode' in user:
            user_data['zip_code'] = user['postalcode'][0]
        if 'ou' in user:
            user_data['org_unit'] = user['ou'][0]
        if 'employeenumber' in user:
            user_data['employee_number'] = user['employeenumber'][0]
        if 'employeetype' in user:
            user_data['employee_type'] = user['employeetype'][0]
        if 'preferredlanguage' in user:
            user_data['preferred_language'] = user['preferredlanguage'][0]
        if 'telephonenumber' in user:
            user_data['phone_number'] = user['telephonenumber'][0]
        if 'manager' in user:
            user_data['manager'] = user['manager'][0]
        if 'memberof_group' in user:
            user_data['member_of'] = user['memberof_group']
        if 'krbpasswordexpiration' in user:
            user_data['krbpasswordexpiration'] = user['krbpasswordexpiration']
        if 'krblastpwdchange' in user:
            user_data['krblastpwdchange'] = user['krblastpwdchange']

        return user_data

    def create_freeipa_user(self, user_id: str, email: str, name: str, lastname: str, user_group: str,
                            full_name: str = '', alias: str = '', job_title: str = '', street_address: str = '',
                            city: str = '', state: str = '', zip_code: str = '', org_unit: str = '',
                            phone_number: str = '', employee_number: str = '', employee_type: str = '',
                            preferred_language: str = '', manager: str = '', update_cache: bool = True) -> (dict, str):
        self.log.info(f'Creating new FreeIPA user {user_id}')

        if "." in user_id and user_group in self.freeipa_gids and self.get_freeipa_user(user_id) is None \
                and self.__is_user_preserved(user_id) is False and email != '' and name != '' and lastname != '':

            if full_name is None or full_name == '':
                full_name = f'{name} {lastname}'

            if alias is None or alias == '':
                alias = self.__generate_alias(name, lastname)

            password = self.__generate_password()

            try:
                # Create the user:
                user = self.freeipa_connection.user_add(
                    a_uid=user_id,
                    o_givenname=name,
                    o_sn=lastname,
                    o_cn=full_name,
                    o_mail=email,
                    o_displayname=full_name,
                    o_gecos=full_name,
                    o_title=job_title,
                    o_street=street_address,
                    o_l=city,
                    o_st=state,
                    o_postalcode=zip_code,
                    o_ou=org_unit,
                    o_employeenumber=employee_number,
                    o_employeetype=employee_type,
                    o_preferredlanguage=preferred_language,
                    o_telephonenumber=phone_number,
                    o_manager=manager,
                    o_gidnumber=str(self.freeipa_gids[user_group]),
                    o_homedirectory=f'/home/{alias}',
                    o_userpassword=password,
                    o_noprivate=True)

                self.log.debug('User account created in FreeIPA')
                self.log.debug(f"User {user_id} created in FreeIPA using temporary password '{password}'")

                # Add user alias:
                self.freeipa_connection.user_add_principal(user_id, alias)
                self.log.debug(f'User alias {alias} added to {user_id} account')

                # Add user to team group:
                self.freeipa_connection.group_add_member(user_group, o_user=user_id)
                self.log.debug(f'User {user_id} added to {user_group} group')

                self.log.info(f'User properly {user_id} created in FreeIPA')

                if update_cache:
                    self.log.debug('Updating FreeIPA cache')
                    self.get_freeipa_users(force_update_cache=True)

                return user, password

            except (freeipa_exceptions.BadRequest,
                    freeipa_exceptions.Denied,
                    freeipa_exceptions.DuplicateEntry,
                    freeipa_exceptions.FreeIPAError,
                    freeipa_exceptions.NotFound,
                    freeipa_exceptions.parse_error,
                    freeipa_exceptions.Unauthorized,
                    freeipa_exceptions.UserLocked,
                    freeipa_exceptions.ValidationError) as e:

                self.log.error(
                    f'Could not create user {user_id} due to a problem with the FreeIPA server: {e}')
                return None

        else:
            self.log.warning(f'User format invalid for {user_id} or {user_group} group not valid')
            return False

    def create_csv_template(self, csv_template_path: str = None) -> bool:
        if not csv_template_path:
            csv_template_path = os.getcwd() + '/' + self.csv_files['import_template']

        self.log.info(f'Creating CSV template at {csv_template_path}')

        header = ['user_id', 'email', 'user_group', 'alias', 'name', 'lastname', 'full_name', 'job_title',
                  'street_address', 'city', 'state', 'zip_code', 'org_unit', 'employee_number', 'employee_type',
                  'preferred_language', 'phone_number', 'manager']

        try:
            with open(csv_template_path, 'w', encoding='UTF8') as f:
                writer = csv.writer(f)
                writer.writerow(header)

            self.log.info('Import CSV template created')
            return True

        except csv.Error:

            self.log.error(f'Could not create the CSV template at {csv_template_path} due to a problem while creating '
                           'the file')
            return False

    def delete_freeipa_user(self, user_id: str, preserve: bool = True) -> bool:
        if preserve:
            self.log.info(f'Deleting FreeIPA user {user_id}')
        else:
            self.log.info(f'Permanently deleting FreeIPA user {user_id}')

        try:
            query_data = self.freeipa_connection.user_del(user_id, o_preserve=preserve)

            if not query_data['result']['failed']:

                self.log.info(f'User {user_id} deleted from FreeIPA')

                self.log.debug('Updating FreeIPA cache')
                self.get_freeipa_users(force_update_cache=True)
                return True
            else:
                self.log.warning(f'User {user_id} deletion failed in FreeIPA')
                return False

        except freeipa_exceptions.NotFound:
            self.log.error(f'Could not delete user {user_id}, it does not exit in the FreeIPA server')
            return False

        except (freeipa_exceptions.BadRequest,
                freeipa_exceptions.Denied,
                freeipa_exceptions.FreeIPAError,
                freeipa_exceptions.NotFound,
                freeipa_exceptions.Unauthorized,
                freeipa_exceptions.UserLocked) as e:

            self.log.error(f'Could not delete user {user_id} due to a problem with the FreeIPA server: {e}')
            return False

    def delete_freeipa_user_otp_tokens(self, user_id: str) -> bool:
        user = self.get_freeipa_user(user_id)

        if user:
            try:
                tokens = self.freeipa_connection.otptoken_find(o_ipatokenowner=user_id)

                if tokens['count'] > 0:

                    success_in_all = True
                    token_count = tokens['count']
                    for i in range(0, token_count):
                        status = self.freeipa_connection.otptoken_del(
                            a_ipatokenuniqueid=tokens['result'][i]['ipatokenuniqueid'],
                            o_continue=True)

                        if status['result']['failed']:
                            success_in_all = False

                    if success_in_all:
                        self.log.info(f'{token_count} OTP token(s) removed for user {user_id}')
                        return True
                    else:
                        self.log.warning(f'Could not remove all of the {token_count} OTP token(s) of user {user_id}')
                        return False
                else:
                    self.log.info(f'User {user_id} has no OTP tokens')
                    return True

            except (freeipa_exceptions.BadRequest,
                    freeipa_exceptions.Denied,
                    freeipa_exceptions.DuplicateEntry,
                    freeipa_exceptions.FreeIPAError,
                    freeipa_exceptions.NotFound,
                    freeipa_exceptions.parse_error,
                    freeipa_exceptions.Unauthorized,
                    freeipa_exceptions.UserLocked,
                    freeipa_exceptions.ValidationError) as e:

                self.log.error(f'Could not complete FreeIPA tasks to handle OTP removal request for user {user_id} due '
                               f'to a problem with the FreeIPA server: {e}')
                return False
        else:
            self.log.warning('Could not remove OTP token(s) of user {user_id}, user not found')

    def disable_freeipa_user(self, user_id: str) -> bool:
        self.log.info(f'Disabling FreeIPA user {user_id}')

        try:
            query_data = self.freeipa_connection.user_disable(user_id)
            return_value = query_data['result']

            if return_value:
                self.log.info(f'User {user_id} disabled in FreeIPA')

            if return_value:
                self.log.debug('Updating FreeIPA cache')
                self.get_freeipa_users(force_update_cache=True)

            return return_value

        except freeipa_exceptions.AlreadyInactive:

            self.log.warning(f'User {user_id} is already disabled')
            return False

        except (freeipa_exceptions.BadRequest,
                freeipa_exceptions.Denied,
                freeipa_exceptions.FreeIPAError,
                freeipa_exceptions.NotFound,
                freeipa_exceptions.Unauthorized,
                freeipa_exceptions.UserLocked) as e:

            self.log.error(
                f'Could not disable user {user_id} due to a problem with the FreeIPA server: {e}')
            return False

    def enable_freeipa_user(self, user_id: str) -> bool:
        self.log.info(f'Enabling FreeIPA user {user_id}')

        try:
            query_data = self.freeipa_connection.user_enable(user_id)
            return_value = query_data['result']

            if return_value:
                self.log.info(f'User {user_id} enabled in FreeIPA')

            if return_value:
                self.log.debug('Updating FreeIPA cache')
                self.get_freeipa_users(force_update_cache=True)

            return return_value

        except freeipa_exceptions.AlreadyActive:

            self.log.warning(f'User {user_id} is already enabled')
            return False

        except (freeipa_exceptions.BadRequest,
                freeipa_exceptions.Denied,
                freeipa_exceptions.FreeIPAError,
                freeipa_exceptions.NotFound,
                freeipa_exceptions.Unauthorized,
                freeipa_exceptions.UserLocked) as e:

            self.log.error(
                f'Could not enable user {user_id} due to a problem with the FreeIPA server: {e}')
            return False

    def export_to_csv(self, export_path: str = None) -> bool:
        if not export_path:
            export_path = os.getcwd() + '/' + self.csv_files['export_file']

        self.log.info(f'Exporting FreeIPA users to {export_path}')

        header = ['user_id', 'email', 'user_group', 'alias', 'name', 'lastname', 'full_name', 'job_title',
                  'street_address', 'city', 'state', 'zip_code', 'org_unit', 'employee_number', 'employee_type',
                  'preferred_language', 'phone_number', 'manager']

        try:
            with open(export_path, 'w', encoding='UTF8') as f:
                writer = csv.writer(f)
                writer.writerow(header)

                freeipa_users = self.get_freeipa_users()

                for user in freeipa_users:

                    user_group = ''

                    for group in freeipa_users[user]['member_of']:
                        if group in self.freeipa_gids:
                            user_group = group
                            break

                    row = [user,
                           freeipa_users[user]['email'],
                           user_group,
                           freeipa_users[user]['alias'][0],
                           freeipa_users[user]['name'],
                           freeipa_users[user]['lastname'],
                           freeipa_users[user]['full_name'],
                           freeipa_users[user]['job_title'],
                           freeipa_users[user]['street_address'],
                           freeipa_users[user]['city'],
                           freeipa_users[user]['state'],
                           freeipa_users[user]['zip_code'],
                           freeipa_users[user]['org_unit'],
                           freeipa_users[user]['employee_number'],
                           freeipa_users[user]['employee_type'],
                           freeipa_users[user]['preferred_language'],
                           freeipa_users[user]['phone_number'],
                           freeipa_users[user]['manager']
                           ]
                    writer.writerow(row)

            self.log.info('Users exported to CSV file')

            return True

        except csv.Error:

            self.log.error(f'Could not export the CSV file at {export_path} due to a problem while creating the file')
            return False

    def get_expired_users(self) -> (dict, dict):
        self.log.info('Obtaining expired users from FreeIPA')

        freeipa_users = self.get_freeipa_users()

        expired_users = {}
        expired_users_disabled = {}

        for user_id in freeipa_users:

            if freeipa_users[user_id]['krblastpwdchange'] != freeipa_users[user_id]['krbpasswordexpiration']:
                delta, exp_date = self.get_user_passwd_expiration(user_id)

                if delta < 0:
                    self.log.info(f'  - {user_id}: expired {abs(delta)} days ago')

                if -self.password_gracious_period <= delta < 0:
                    expired_users[user_id] = delta

                elif delta < -self.password_gracious_period:
                    expired_users_disabled[user_id] = delta

        return expired_users, expired_users_disabled

    def get_freeipa_admin_emails(self) -> str:
        self.log.info('Obtaining emails of FreeIPA admins')

        freeipa_users = self.get_freeipa_users()

        admin_emails = ''

        for user in freeipa_users:
            if 'admins' in freeipa_users[user]['member_of']:
                admin_emails += f"{freeipa_users[user]['full_name']} <{freeipa_users[user]['email']}>, "
                self.log.debug(f"{freeipa_users[user]['full_name']} <{freeipa_users[user]['email']}>")

        if admin_emails:
            admin_emails = admin_emails[:len(admin_emails)-2]
            self.log.info('FreeIPA admin emails retrieved')
        else:
            self.log.error('No FreeIPA admin emails retrieved')

        return admin_emails

    def get_freeipa_user(self, user_id: str) -> dict:
        freeipa_users = self.cache_handler.get_freeipa_cache()

        if freeipa_users:
            self.log.info(f'Obtaining information of user {user_id} from FreeIPA cache')
            if user_id in freeipa_users:
                self.log.debug(f'User {user_id} retrieved from FreeIPA cache')
                return freeipa_users[user_id]
            else:
                self.log.debug(f'User {user_id} does not exist in FreeIPA cache')
                return None
        else:
            self.log.info(f'Obtaining information of user {user_id} from FreeIPA')
            try:
                if self.freeipa_connection:
                    query_data = self.freeipa_connection.user_find(o_uid=user_id.lower(), o_preserved=False)

                    if query_data['result']:
                        user = query_data['result'][0]

                        user_data = self.__get_user_data(user)
                        self.log.info(f'User information for {user_id} retrieved from FreeIPA')

                        return user_data

                    else:
                        self.log.info('User does not exist in FreeIPA')
                        return None
                else:
                    self.log.error(
                        'Could not obtain user data due to a problem with the FreeIPA connection object')
                    return None

            except (freeipa_exceptions.BadRequest,
                    freeipa_exceptions.Denied,
                    freeipa_exceptions.FreeIPAError,
                    freeipa_exceptions.NotFound,
                    freeipa_exceptions.Unauthorized,
                    freeipa_exceptions.UserLocked) as e:

                self.log.error(f'Could not obtain user data due to a problem with the FreeIPA server: {e}')
                return None

    def get_freeipa_users(self, force_update_cache: bool = False) -> dict:
        self.log.info('Obtaining FreeIPA users')
        freeipa_users = self.cache_handler.get_freeipa_cache()

        if freeipa_users and not force_update_cache:

            self.log.info('Users retrieved from FreeIPA cache')
            return freeipa_users

        else:
            self.log.info('Obtaining users from FreeIPA')
            try:
                if self.freeipa_connection:
                    freeipa_users = {}

                    for group in self.freeipa_gids:

                        group_data = self.freeipa_connection.user_find(o_in_group=group, o_preserved=False)

                        for user in group_data['result']:

                            user_id = user['uid'][0]
                            freeipa_users[user_id] = self.__get_user_data(user)
                            self.log.debug(f'Information for user {user_id} retrieved from FreeIPA')

                    self.log.info('Users retrieved from FreeIPA server')

                    self.log.debug('Saving FreeIPA users to cache file')
                    save_status = self.cache_handler.save_cache(freeipa_users=freeipa_users)

                    if save_status:
                        self.log.debug('FreeIPA user cache successfully saved')
                    else:
                        self.log.warning('FreeIPA user cache could not be saved')

                    return freeipa_users

                else:
                    return None

            except (freeipa_exceptions.BadRequest,
                    freeipa_exceptions.Denied,
                    freeipa_exceptions.FreeIPAError,
                    freeipa_exceptions.NotFound,
                    freeipa_exceptions.Unauthorized,
                    freeipa_exceptions.UserLocked) as e:

                self.log.error(f'Could not obtain user list due to a problem with the FreeIPA server: {e}')

                return None

    def get_user_passwd_expiration(self, user_id: str) -> (int, datetime.date):
        self.log.debug(f'Obtaining user {user_id} password expiration info')

        user = self.get_freeipa_user(user_id)

        if 'krbpasswordexpiration' in user and user['krbpasswordexpiration'] != '':

            timestamp = user['krbpasswordexpiration'][0]['__datetime__']

            today = datetime.date.today()
            exp_date = datetime.datetime.strptime(timestamp, '%Y%m%d%H%M%SZ').date()
            delta = exp_date - today
            self.log.debug(f'Password for {user_id} to expire in {delta.days} days')

            return delta.days, exp_date

        else:
            self.log.warning(f'Password for {user_id} not set yet')
            return 365, (datetime.datetime.now() + datetime.timedelta(days=365)).date()

    def get_users_no_password(self) -> list:
        self.log.info('Obtaining users pending password change from FreeIPA')

        freeipa_users = self.get_freeipa_users()

        users_no_password = []

        for user_id in freeipa_users:
            if freeipa_users[user_id]['krblastpwdchange'] == freeipa_users[user_id]['krbpasswordexpiration']:
                users_no_password.append(user_id)
                self.log.debug(f' - {user_id}')

        if users_no_password:
            self.log.info('Finished obtaining users pending password change')
        else:
            self.log.info('There are no users pending password change at this time')

        return users_no_password

    def import_from_csv(self, import_path: str = None) -> (dict, list, list, list):
        if not import_path:
            import_path = os.getcwd() + '/' + self.csv_files['import_file']

        self.log.info(f'Importing user data to FreeIPA from {import_path}')

        imported_users = {}
        updated_users = []
        skipped_users = []
        not_imported_users = []
        skipped_users_data = {}

        if os.path.exists(import_path):
            try:
                with open(import_path, newline='') as csvfile:
                    reader = csv.DictReader(csvfile)

                    for row in reader:

                        user_id = row['user_id'].strip()
                        if not self.get_freeipa_user(user_id):
                            import_data = {}
                            for key in row:
                                import_data[key] = row[key].strip()

                            user, password = self.create_freeipa_user(**import_data, update_cache=False)

                            if password:
                                imported_users[row['user_id']] = password
                                self.log.debug(f"User {user_id} imported to FreeIPA")

                            else:
                                not_imported_users.append(row['user_id'])
                                self.log.warning(f"User {row['user_id']} not imported to FreeIPA")

                        else:
                            skipped_users.append(row['user_id'])
                            skipped_users_data[row['user_id']] = row

                for user in skipped_users:
                    import_data = {}

                    for key in skipped_users_data[user]:
                        if skipped_users_data[user][key] != '' and key != 'alias':
                            import_data[key] = skipped_users_data[user][key].strip()

                    freeipa_user = self.get_freeipa_user(user)

                    new_import_data = {'user_id': user}

                    for key in import_data:
                        if key in freeipa_user and import_data[key] != freeipa_user[key]:
                            new_import_data[key] = import_data[key]

                        if key == 'user_group' and import_data[key] not in freeipa_user['member_of']:
                            new_import_data[key] = import_data[key]

                    if new_import_data:

                        import_status = self.update_freeipa_user(**new_import_data, update_cache=False)

                        if import_status:
                            updated_users.append(user)
                            skipped_users.pop(skipped_users.index(user))
                            self.log.debug(f'User {user} updated in FreeIPA')
                    else:
                        self.log.warning(f'User {user} is up-to-date in FreeIPA, nothing to update')

                if imported_users != {} or updated_users != []:
                    self.log.info('Users imported and/or updated from CSV file')
                    self.log.debug('Updating FreeIPA cache')
                    self.get_freeipa_users(force_update_cache=True)

                elif imported_users == {} and updated_users == []:
                    self.log.info('No user was modified from data in CSV file')

                return imported_users, updated_users, skipped_users, not_imported_users

            except csv.Error:
                self.log.error(f'Could not import users from CSV file {import_path} due to a  problem while accessing '
                               'the file.')
                return None, None, None, None
        else:
            self.log.error(f'Import file {import_path} does not exist')
            return None, None, None, None

    def reset_user_password(self, user_id: str) -> str:
        self.log.debug(f'Resetting password for user {user_id}')
        user = self.get_freeipa_user(user_id)

        if user:
            password = self.__generate_password()

            try:
                self.freeipa_connection.user_mod(a_uid=user_id, o_userpassword=password)
                self.log.debug(f'Password for user {user_id} changed to {password}')
                return password

            except (freeipa_exceptions.BadRequest,
                    freeipa_exceptions.Denied,
                    freeipa_exceptions.FreeIPAError,
                    freeipa_exceptions.NotFound,
                    freeipa_exceptions.Unauthorized,
                    freeipa_exceptions.UserLocked) as e:

                self.log.error(f'Password for user {user_id} could not be changed due to an error with FreeIPA: {e}')
                return None
        else:
            self.log.error(
                f'User {user_id} does not exist, password not changed')
            return None

    def update_freeipa_user(self, user_id: str, email: str = None, name: str = None,
                            lastname: str = None, full_name: str = None,
                            initials: str = None, user_group: str = None,
                            job_title: str = None, street_address: str = None,
                            city: str = None, state: str = None,
                            zip_code: str = None, org_unit: str = None,
                            phone_number: str = None, employee_number: str = None,
                            employee_type: str = None,
                            preferred_language: str = None,
                            manager: str = None, home_directory: str = None,
                            update_cache: bool = True) -> bool:
        self.log.info(f'Updating FreeIPA user {user_id}')

        return_value = False

        user = self.get_freeipa_user(user_id)

        if "." in user_id and user is not None \
                and (user_group is None or (user_group is not None and user_group in self.freeipa_gids)) \
                and (manager is None or (manager is not None and self.get_freeipa_user(manager) is not None)):

            if name and lastname:
                if not full_name:
                    full_name = f'{name} {lastname}'
                if not initials:
                    initials = name[:1] + lastname[:1]

            elif name:
                if not full_name:
                    full_name = f"{name} {user['lastname']}"
                if not initials:
                    initials = name[:1] + user['lastname'][:1]

            elif lastname:
                if not full_name:
                    full_name = f"{user['name']} {lastname}"
                if not initials:
                    initials = user['name'][:1] + lastname[:1]

            try:

                if email is not None or name is not None or lastname is not None or job_title is not None \
                        or street_address is not None or city is not None or state is not None \
                        or zip_code is not None or org_unit is not None or phone_number is not None \
                        or employee_number is not None or employee_type is not None or preferred_language is not None \
                        or manager is not None or home_directory is not None or full_name is not None \
                        or initials is not None:
                    self.freeipa_connection.user_mod(a_uid=user_id, o_mail=email,
                                                     o_givenname=name, o_sn=lastname,
                                                     o_title=job_title,
                                                     o_street=street_address, o_l=city,
                                                     o_st=state, o_postalcode=zip_code,
                                                     o_ou=org_unit,
                                                     o_telephonenumber=phone_number,
                                                     o_employeenumber=employee_number,
                                                     o_employeetype=employee_type,
                                                     o_preferredlanguage=preferred_language,
                                                     o_displayname=full_name,
                                                     o_cn=full_name, o_gecos=full_name,
                                                     o_initials=initials,
                                                     o_manager=manager,
                                                     o_homedirectory=home_directory)

                    self.log.debug('User account updated in FreeIPA')
                    return_value = True

                if user_group is not None:
                    if user_group not in user['member_of']:
                        for group in user['member_of']:
                            if group in self.freeipa_gids:
                                self.freeipa_connection.group_remove_member(
                                    group, o_user=user_id)
                                self.log.debug(f'User {user_id} removed from group {group}')

                        self.freeipa_connection.group_add_member(user_group, o_user=user_id)
                        self.log.debug(f'User {user_id} added to group {user_group}')
                        return_value = True

                self.log.info('User fully updated in FreeIPA')

            except (freeipa_exceptions.BadRequest,
                    freeipa_exceptions.Denied,
                    freeipa_exceptions.DuplicateEntry,
                    freeipa_exceptions.FreeIPAError,
                    freeipa_exceptions.NotFound,
                    freeipa_exceptions.parse_error,
                    freeipa_exceptions.Unauthorized,
                    freeipa_exceptions.UserLocked,
                    freeipa_exceptions.ValidationError) as e:

                self.log.error(f'Could not update user {user_id} due to a problem with the FreeIPA server: {e}')
                return_value = False
        else:
            self.log.warning(f'User does not exist or invalid user_id format used for {user_id}')

        if return_value and update_cache:
            self.log.debug('Updating FreeIPA cache')
            self.get_freeipa_users(force_update_cache=True)

        return return_value
