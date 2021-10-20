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

import ldap
from ldap.controls import SimplePagedResultsControl

from utils.cache_handler import CacheHandler


class ADHandler:

    def __init__(self, ad_settings: dict, cache_handler: CacheHandler, corporate_email_domains: list):
        self.log = logging.getLogger('freeipa_manager')
        self.ad_credentials = ad_settings['credentials']
        self.ad_base = ad_settings['base']
        self.cache_handler = cache_handler
        self.corporate_email_domains = corporate_email_domains
        self.ad_connection = self.__connect_to_ad()

    def __connect_to_ad(self) -> ldap.ldapobject:
        self.log.debug('Connecting to AD server')

        ad_server = self.ad_credentials['proto'] + self.ad_credentials['host'] + ':' + str(self.ad_credentials['port'])

        try:
            ad_client = ldap.initialize(ad_server)
            ad_client.set_option(ldap.OPT_REFERRALS, 0)
            ad_client.simple_bind_s(self.ad_credentials['username'], self.ad_credentials['password'])

            self.log.debug('Connection established')
            return ad_client

        except (ldap.BUSY,
                ldap.CONNECT_ERROR,
                ldap.INAPPROPRIATE_AUTH,
                ldap.INSUFFICIENT_ACCESS,
                ldap.INVALID_CREDENTIALS,
                ldap.PROTOCOL_ERROR,
                ldap.SERVER_DOWN,
                ldap.TIMEOUT,
                ldap.UNAVAILABLE) as e:

            self.log.error(f'Could not connect to AD server {ad_server}: {e}')
            return None

    def __get_uid_from_ad_user_base(self, user_base: str) -> str:
        self.log.debug(f"Translating AD user base {user_base} to FreeIPA's user_id format")

        search_flt = '(objectClass=person)'

        try:
            msgid = self.ad_connection.search_ext(base=user_base,
                                                  scope=ldap.SCOPE_SUBTREE,
                                                  filterstr=search_flt,
                                                  attrlist=['mail'])

            query_data = self.ad_connection.result3(msgid)[1]

            if 'mail' in query_data[0][1]:
                email = query_data[0][1]['mail'][0].decode('utf-8')
                user_id = email[:email.index('@')].lower()

                self.log.debug(f'User ID found: {user_id}')

                return user_id
            else:
                self.log.debug('User ID not found')
                return ''

        except (ldap.LDAPError,
                ldap.BUSY,
                ldap.CONNECT_ERROR,
                ldap.INAPPROPRIATE_AUTH,
                ldap.INSUFFICIENT_ACCESS,
                ldap.INVALID_CREDENTIALS,
                ldap.NO_RESULTS_RETURNED,
                ldap.NO_SUCH_ATTRIBUTE,
                ldap.NO_SUCH_OBJECT,
                ldap.PROTOCOL_ERROR,
                ldap.RESULTS_TOO_LARGE,
                ldap.SERVER_DOWN,
                ldap.SIZELIMIT_EXCEEDED,
                ldap.TIMELIMIT_EXCEEDED,
                ldap.TIMEOUT,
                ldap.UNAVAILABLE) as e:

            self.log.error(f'Could not resolve user_id due to a problem with the AD server: {e}')
            return ''

    @staticmethod
    def __get_user_data(user) -> dict:
        email = user[1]['mail'][0].decode('utf-8').lower()
        user_data = {'email': email, 'alias': '', 'full_name': '', 'name': '', 'lastname': '', 'job_title': '',
                     'street_address': '', 'city': '', 'state': '', 'zip_code': '', 'org_unit': '',
                     'employee_number': '', 'employee_type': '', 'preferred_language': '', 'phone_number': '',
                     'manager': '', 'cn': '', 'member_of': ''}

        if 'sAMAccountName' in user[1]:
            user_data['alias'] = user[1]['sAMAccountName'][0].decode('utf-8').lower().strip()
        if 'name' in user[1]:
            user_data['full_name'] = user[1]['name'][0].decode('utf-8').strip()
        if 'givenName' in user[1]:
            user_data['name'] = user[1]['givenName'][0].decode('utf-8').strip()
        if 'sn' in user[1]:
            user_data['lastname'] = user[1]['sn'][0].decode('utf-8').strip()
        if 'title' in user[1]:
            user_data['job_title'] = user[1]['title'][0].decode('utf-8').strip()
        if 'streetAddress' in user[1]:
            user_data['street_address'] = user[1]['streetAddress'][0].decode('utf-8').strip()
        if 'l' in user[1]:
            user_data['city'] = user[1]['l'][0].decode('utf-8').strip()
        if 'postalCode' in user[1]:
            user_data['zip_code'] = user[1]['postalCode'][0].decode('utf-8').strip()
        if 'st' in user[1]:
            user_data['state'] = user[1]['st'][0].decode('utf-8').strip()
        if 'telephoneNumber' in user[1]:
            user_data['phone_number'] = user[1]['telephoneNumber'][0].decode('utf-8').strip()
        if 'department' in user[1]:
            user_data['org_unit'] = user[1]['department'][0].decode('utf-8').strip()
        if 'employeeID' in user[1]:
            user_data['employee_number'] = user[1]['employeeID'][0].decode('utf-8').strip()
        if 'extensionAttribute6' in user[1]:
            user_data['employee_type'] = user[1]['extensionAttribute6'][0].decode('utf-8').strip()
        if 'msExchUserCulture' in user[1]:
            user_data['preferred_language'] = user[1]['msExchUserCulture'][0].decode('utf-8').strip()
        if 'manager' in user[1]:
            manager = user[1]['manager'][0].decode('utf-8')
            user_data['manager'] = manager[:manager.index(',')][3:].strip()
        if 'cn' in user[1]:
            user_data['cn'] = user[1]['cn'][0].decode('utf-8').strip()
        if 'memberOf' in user[1]:
            member_of = []
            for group in user[1]['memberOf']:
                member_of.append(group.decode('utf-8').strip())
            user_data['member_of'] = member_of

        return user_data

    def __update_manager_ids(self, ad_users: dict, cn_uid_pairs: dict) -> dict:
        self.log.debug("Converting AD manager fields to FreeIPA's user_id format")

        if ad_users:
            for user in ad_users:
                if ad_users[user]['manager'] in cn_uid_pairs:

                    manager = cn_uid_pairs[ad_users[user]['manager']]
                    ad_users[user]['manager'] = manager

                    self.log.debug(f'Manager ID for {user} set to {manager}')

                else:
                    ad_users[user]['manager'] = ''
                    self.log.debug(f'Manager ID for {user} not found')

            self.log.debug('AD manager fields converted to user_id format')
        else:
            self.log.warning('Empty AD user list provided')

        return ad_users

    def get_ad_user(self, user_id: str) -> dict:
        ad_users = self.cache_handler.get_ad_cache()

        if ad_users:
            self.log.info(f'Obtaining information of user {user_id} from AD cache')
            if user_id in ad_users:
                self.log.debug(f'User {user_id} retrieved from AD cache')
                return ad_users[user_id]
            else:
                self.log.debug(f'User {user_id} does not exist in AD cache')
                return None
        else:
            self.log.info(f'Obtaining information of user {user_id} from AD')
            try:
                if self.ad_connection:
                    search_flt = f'(&(objectClass=person)(mail={user_id}*))'

                    searchreq_attrlist = ['mail', 'sAMAccountName', 'name', 'givenName', 'sn', 'title', 'streetAddress',
                                          'l', 'postalCode', 'st', 'telephoneNumber', 'department', 'employeeID',
                                          'extensionAttribute6', 'msExchUserCulture', 'manager', 'memberOf']

                    msgid = self.ad_connection.search_ext(base=self.ad_base,
                                                          scope=ldap.SCOPE_SUBTREE,
                                                          filterstr=search_flt,
                                                          attrlist=searchreq_attrlist)

                    query_data = self.ad_connection.result3(msgid)[1]

                    if query_data:
                        user = query_data[0]

                        email = user[1]['mail'][0].decode('utf-8').lower()
                        email_domain = email[email.index('@') + 1:]

                        if email_domain in self.corporate_email_domains:
                            user_data = self.__get_user_data(user)
                            self.log.info(f'User information for {user_id} retrieved from AD')

                            return user_data

                        else:
                            self.log.warning(f'User {user_id} skipped, email {email} not valid corporate domain')
                            return None
                    else:
                        self.log.warning(f'User {user_id} does not exist in AD')
                        return None
                else:
                    self.log.error('Could not obtain user data due to a problem with the AD connection object')
                    return None

            except (ldap.LDAPError,
                    ldap.BUSY,
                    ldap.CONNECT_ERROR,
                    ldap.INAPPROPRIATE_AUTH,
                    ldap.INSUFFICIENT_ACCESS,
                    ldap.INVALID_CREDENTIALS,
                    ldap.NO_RESULTS_RETURNED,
                    ldap.NO_SUCH_ATTRIBUTE,
                    ldap.NO_SUCH_OBJECT,
                    ldap.PROTOCOL_ERROR,
                    ldap.RESULTS_TOO_LARGE,
                    ldap.SERVER_DOWN,
                    ldap.SIZELIMIT_EXCEEDED,
                    ldap.TIMELIMIT_EXCEEDED,
                    ldap.TIMEOUT,
                    ldap.UNAVAILABLE) as e:

                self.log.error(f'Could not obtain user information due to a problem with the AD server: {e}')
                return None

    def get_ad_users(self, force_update_cache: bool = False) -> dict:
        self.log.info('Obtaining AD users')
        ad_users = self.cache_handler.get_ad_cache()

        if ad_users and not force_update_cache:

            self.log.debug('Users retrieved from AD cache')
            return ad_users

        else:
            self.log.info('Obtaining users from AD')
            try:
                if self.ad_connection:
                    page_size = 1000
                    search_flt = '(objectClass=person)'

                    searchreq_attrlist = ['mail', 'sAMAccountName', 'name', 'givenName', 'sn', 'title', 'streetAddress',
                                          'l', 'postalCode', 'st', 'telephoneNumber', 'department', 'employeeID',
                                          'extensionAttribute6', 'msExchUserCulture', 'manager', 'cn', 'memberOf']

                    req_ctrl = SimplePagedResultsControl(criticality=True, size=page_size, cookie='')

                    msgid = self.ad_connection.search_ext(base=self.ad_base,
                                                          scope=ldap.SCOPE_SUBTREE,
                                                          filterstr=search_flt,
                                                          attrlist=searchreq_attrlist,
                                                          serverctrls=[req_ctrl])

                    ad_users = {}
                    cn_uid_pairs = {}
                    pages = 0

                    # Loop over all of the pages using the same cookie, otherwise
                    # the search will fail

                    while True:

                        pages += 1
                        rtype, rdata, rmsgid, serverctrls = self.ad_connection.result3(msgid)

                        for user in rdata:

                            if 'mail' in user[1]:

                                email = user[1]['mail'][0].decode('utf-8').lower()
                                user_id = email[:email.index('@')]
                                email_domain = email[email.index('@') + 1:]

                                if email_domain in self.corporate_email_domains:

                                    if 'cn' in user[1]:
                                        user_cn = user[1]['cn'][0].decode('utf-8').strip()
                                        cn_uid_pairs[user_cn] = user_id

                                    ad_users[user_id] = self.__get_user_data(user)
                                    self.log.debug(f'User {user_id} information retrieved from AD')

                        pctrls = [c for c in serverctrls if c.controlType == SimplePagedResultsControl.controlType]

                        if pctrls:
                            if pctrls[0].cookie:
                                req_ctrl.cookie = pctrls[0].cookie
                                msgid = self.ad_connection.search_ext(base=self.ad_base,
                                                                      scope=ldap.SCOPE_SUBTREE,
                                                                      filterstr=search_flt,
                                                                      attrlist=searchreq_attrlist,
                                                                      serverctrls=[req_ctrl])
                            else:
                                break
                        else:
                            break

                    ad_users = self.__update_manager_ids(ad_users, cn_uid_pairs)

                    self.log.info('Users retrieved from AD server')

                    self.log.debug('Saving AD users to cache file')
                    save_status = self.cache_handler.save_cache(ad_users=ad_users)

                    if save_status:
                        self.log.debug('AD user cache successfully saved')
                    else:
                        self.log.debug('AD user cache could not be saved')

                    return ad_users
                else:
                    return None

            except (ldap.LDAPError,
                    ldap.BUSY,
                    ldap.CONNECT_ERROR,
                    ldap.INAPPROPRIATE_AUTH,
                    ldap.INSUFFICIENT_ACCESS,
                    ldap.INVALID_CREDENTIALS,
                    ldap.NO_RESULTS_RETURNED,
                    ldap.NO_SUCH_ATTRIBUTE,
                    ldap.NO_SUCH_OBJECT,
                    ldap.PROTOCOL_ERROR,
                    ldap.RESULTS_TOO_LARGE,
                    ldap.SERVER_DOWN,
                    ldap.SIZELIMIT_EXCEEDED,
                    ldap.TIMELIMIT_EXCEEDED,
                    ldap.TIMEOUT,
                    ldap.UNAVAILABLE) as e:

                self.log.error(f'Could not obtain user list due to a problem with the AD server: {e}')

                return None
