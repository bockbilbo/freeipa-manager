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

import argparse


class Menu:

    def __init__(self, log_file: str, cache_files: dict, csv_files: dict, freeipa_gids: dict,
                 valid_sync_email_domains: list, cache_path: str, cache_validity: int, password_gracious_period: int,
                 notification_days: list):

        self.log_file = log_file
        self.cache_files = cache_files
        self.csv_files = csv_files
        self.freeipa_gids = freeipa_gids
        self.valid_sync_email_domains = self.__get_string_from_list(list(valid_sync_email_domains))
        self.cache_path = cache_path
        self.cache_validity = cache_validity
        self.password_gracious_period = password_gracious_period
        self.notification_days = notification_days

    @staticmethod
    def __get_string_from_list(input_list: list) -> str:
        if len(input_list) > 0 and type(input_list[0]) is not str:
            input_list = [str(element) for element in input_list]

        if len(input_list) > 2:
            joined_string = ', '.join(input_list)
            last_comma = joined_string.rfind(', ')
            joined_string = joined_string[:last_comma] + joined_string[last_comma:].replace(', ', ' and ')
            return joined_string

        elif len(input_list) == 2:
            return ' and '.join(input_list)

        elif len(input_list) == 1:
            return input_list[0]

        else:
            return ''

    def generate_menu(self) -> (argparse.ArgumentParser, argparse.Namespace):
        valid_user_groups = self.__get_string_from_list(list(self.freeipa_gids))

        argparser = argparse.ArgumentParser(

            description='FreeIPA Manager is a program conceived to facilitate user management in FreeIPA, offering '
                        'batch user imports and updates, user synchronization with Active Directory or password '
                        'expiration email notifications among other things. '
                        'Read the help output below to understand all the options available.')

        main_functions = argparser.add_mutually_exclusive_group(required=True)

        main_functions.add_argument('-s', '--check-servers',
                                    help='checks the reachability of the SMTP, FreeIPA and AD servers performing a '
                                         'simple TCP port analysis for SMTP, HTTPS and LDAPS. '
                                         'The program will always check the availability of the servers upon '
                                         'execution, but this option is useful for quick health checks',
                                    action='store_true')

        main_functions.add_argument('-b', '--check-cache',
                                    help='checks the status of the FreeIPA and AD user cache.'
                                         f'The cache is only valid for {self.cache_validity} minutes and it is stored '
                                         f'in JSON files located at {self.cache_path}. '
                                         'Direct queries to the servers usually add a handful of seconds to the '
                                         'program execution time, hence the reason for caching. '
                                         'The program will automatically update the cache if not available or expired '
                                         'and this option is useful for quick health checks ',
                                    action='store_true')

        main_functions.add_argument('-a', '--update-ad-cache',
                                    help=f"updates the local AD user cache stored at {self.cache_files['ad_cache']}. "
                                         'This cache is updated automatically when the file is missing or upon cache '
                                         f"expiration after {self.cache_validity} minutes. "
                                         'Caching the AD user database reduces the program execution time and manual '
                                         'cache updates should not be required unless you are aware of a recent AD '
                                         'change needed for an import/update/sync task',
                                    action='store_true')

        main_functions.add_argument('-f', '--update-freeipa-cache',
                                    help='updates the local FreeIPA user cache stored at '
                                         f"{self.cache_files['freeipa_cache']}. "
                                         'This cache is updated automatically when the file is missing, upon cache '
                                         f"expiration after {self.cache_validity} minutes and when performing database "
                                         'update tasks like adding, modifying, disabling, enabling, deleting, or '
                                         'synchronizing user accounts. '
                                         'The FreeIPA user cache reduces the program execution time and manual '
                                         'cache updates should not be required unless you are aware of a recent '
                                         'FreeIPA DB change needed for an import/update/sync task',
                                    action='store_true')

        main_functions.add_argument('-c', '--update-cache-files',
                                    help='updates both the local AD and FreeIPA user caches stored at '
                                         f"at {self.cache_files['ad_cache']} and {self.cache_files['freeipa_cache']}. "
                                         'Read the option descriptions of -a (--update-ad-cache) and -f '
                                         '(--update-freeipa-cache) for more information on caching',
                                    action='store_true')

        main_functions.add_argument('-g', '--delete-cache',
                                    help='deletes the local AD and FreeIPA user caches stored at '
                                         f"{self.cache_files['ad_cache']} and {self.cache_files['freeipa_cache']}. "
                                         'This option is useful when debugging the application and should not be '
                                         'needed for normal operations. '
                                         'Use the -c (--update-cache-files) option if you want to renew the local '
                                         'cache',
                                    action='store_true')

        main_functions.add_argument('-d', '--disable-user',
                                    help='disables the user provided in the argument. '
                                         'The given user name must use the dotted user_id format, following '
                                         'the first.lastname naming convention used for corporate email addresses. '
                                         'Disabled users maintain their group memberships and aliases, and can be '
                                         're-enabled from command line with the -e (--enable-user) option . '
                                         "Admins can also disable users from FreeIPA's web GUI directly",
                                    metavar='USER_ID')

        main_functions.add_argument('-e', '--enable-user',
                                    help='enables the user provided in the argument. '
                                         'The given user name must use the dotted user_id format, following the '
                                         'first.lastname naming convention used for corporate email addresses. '
                                         "Admins can also enable users from FreeIPA's web GUI directly",
                                    metavar='USER_ID')

        main_functions.add_argument('-w', '--delete-user',
                                    help='deletes the user provided in the argument. '
                                         'The given user name must use the dotted user_id format, following the '
                                         'first.lastname naming convention used for corporate email addresses. '
                                         "Deleted users are automatically disabled, moved to the 'preserved users' "
                                         'group, and can only be re-enabled using the FreeIPA Web GUI. '
                                         'Keep in mind that when users are deleted and moved to the preserved '
                                         'status, they lose their user groups, alias information and password. '
                                         'These will need to be re-configured manually from the Web GUI upon user '
                                         're-activation',
                                    metavar='USER_ID')

        main_functions.add_argument('-o', '--delete-user-otp-tokens',
                                    help='deletes all the OTP tokens linked with the user provided in the argument. '
                                         'The given user name must use the dotted user_id format, following '
                                         'the first.lastname naming convention used for corporate email addresses. '
                                         'When FreeIPA users set OTP access they must append 6 temporary digits '
                                         'generated by their token to their passwords when using their accounts. '
                                         'If users lose access to their tokens they will not be able to access the '
                                         'system. '
                                         'This option is useful to easily unlock users unable to use their accounts '
                                         'due lost OTP tokens',
                                    metavar='USER_ID')

        main_functions.add_argument('-r', '--reset-user-password',
                                    help='resets the password for the user specified in the argument and notifies the '
                                         'change. '
                                         'The given user name must exist in the user database and must use the dotted '
                                         'user_id format, following the first.lastname naming convention used for '
                                         'corporate email addresses. '
                                         "The program will obtain the user's email from the FreeIPA database and "
                                         'send a notification prompting the user to change the password. '
                                         'This option is useful to quickly reset user passwords with random strings',
                                    metavar='USER_ID')

        main_functions.add_argument('-m', '--list-expired-users',
                                    help='prints the list of users with expired passwords, including the time past '
                                         'since expiration. '
                                         'Keep in mind that expired users are not allowed to access servers managed by '
                                         'FreeIPA, but still can use their credentials for LDAP authentication, '
                                         'commonly used for internal tools, TACACS and RADIUS. '
                                         'To restrict the access of users in this scenario, the program will disable '
                                         'users with passwords expired for more than the gracious period of '
                                         f'{self.password_gracious_period} days, forcing users to contact support to '
                                         'restore their account. '
                                         'The evaluation of expired users is performed when calling option -k '
                                         '(--process-password-expirations)',
                                    action='store_true')

        main_functions.add_argument('-n', '--list-users-no-password',
                                    help='prints the list of users whose password was reset but not changed, including '
                                         'users disabled for not changing their password within the gracious period of '
                                         f'{self.password_gracious_period} days after expiration. '
                                         'This option is useful to get a quick status of inactive users in order to '
                                         'to evaluate their deletion from the system',
                                    action='store_true')

        main_functions.add_argument('-x', '--export-users',
                                    help='exports the existing FreeIPA user database into the CSV file specified '
                                         'by the argument. '
                                         'If no file path given, the data export will be saved as '
                                         f"./{self.csv_files['export_file']}. "
                                         'Keep in mind that the exported data will exclude system users in FreeIPA, '
                                         'only saving data of users belonging to the following groups: '
                                         f'{valid_user_groups}. ',
                                    dest='export_file',
                                    const='',
                                    nargs='?',
                                    metavar='FILE_PATH')

        main_functions.add_argument('-i', '--import-users',
                                    help='imports user data into FreeIPA from the CSV file specified by the argument, '
                                         'creating or updating users as needed. '
                                         "The user_id field is mandatory for both actions and must match the user's "
                                         'corporate email address user using the dotted format (i.e. first.lastname). '
                                         'New users will need to have at least an email, name, lastname and user_group '
                                         'populated upon import. '
                                         'The user_group field must match one of the following values: '
                                         f'{valid_user_groups}. '
                                         'Keep in mind that users can only belong to a single group. '
                                         'When updating the group of an existing user, membership will be revoked for '
                                         'its previous group. '
                                         'Additionally, if included, the manager field must contain the user_id of the '
                                         "user's manager, who must exist in the FreeIPA database. "
                                         'Keep in mind that most of the data imported through this option will be '
                                         "overwritten for users built in the AD server upon server synchronization "
                                         'via the -u (--update-from-ad) option. '
                                         'If no file path is provided as an argument, the script will attempt to '
                                         f"load import data from ./{self.csv_files['import_file']}",
                                    dest='import_file',
                                    const='',
                                    nargs='?',
                                    metavar='FILE_PATH')

        main_functions.add_argument('-t', '--import-template',
                                    help='creates an empty CSV template file at at the given location to be used for '
                                         'user imports with the -i (--import-users) option. '
                                         'If no file path is provided as an argument, the program will attempt to'
                                         f"create the template at ./{self.csv_files['import_template']}",
                                    dest='template_file',
                                    const='',
                                    nargs='?',
                                    metavar='FILE_PATH')

        main_functions.add_argument('-u', '--update-from-ad',
                                    help='updates the existing FreeIPA user data with information available from AD. '
                                         'The program will compare users one by one, prioritizing AD information '
                                         'for those with an email address in one of the following domains: '
                                         f'{self.valid_sync_email_domains}. '
                                         "Users with emails of other domains are out of the AD server scope "
                                         'and their information cannot be retrieved through AD LDAP lookups. '
                                         'Additionally, synchronization will be restricted only to FreeIPA users '
                                         'belonging to the following groups: '
                                         f'{valid_user_groups}. '
                                         'During synchronization, the following FreeIPA user fields will be '
                                         'overwritten if a different -not empty- value is found on AD: '
                                         'email address, name, last name, full name, job title, street address, city '
                                         'state, zip code, department, employee number, employee type, preferred '
                                         'language, phone number and manager -if exists in FreeIPA',
                                    action='store_true')

        main_functions.add_argument('-k', '--process-password-expirations',
                                    help='reviews the password expiration dates for all the existing FreeIPA users, '
                                         'notifies users close to expiration and disables those whose password has '
                                         f'been expired over the gracious period of {self.password_gracious_period} '
                                         'days. '
                                         'Password reset reminders are sent to those with passwords set to expire in '
                                         f'the next {self.__get_string_from_list(self.notification_days)} days. '
                                         'Notified users are logged in a local cache located at '
                                         f"{self.cache_files['freeipa_cache']} to prevent spamming. "
                                         'Keep in mind that used password policies might differ between existing user '
                                         "groups depending on FreeIPA's configuration. "
                                         'Policies define rules for passwords such as the maximum lifetime, history '
                                         'size, character types or length. '
                                         "Password policies can be reviewed and modified by admins from FreeIPA's Web "
                                         'GUI at Policy -> Password Policies. '
                                         'The -k (--process-password-expirations) option is designed to be run on a '
                                         'daily cronjob to automate notifications',
                                    action='store_true')

        main_functions.add_argument('-l', '--process-terminated-users',
                                    help='compares the FreeAIPA users against AD and deletes terminated users from the '
                                         'database. '
                                         "User termination evaluation is performed based on the user's group and "
                                         'email domain.'
                                         'A user must belong to any of the following groups in order to be '
                                         f'evaluated for termination: {valid_user_groups}. '
                                         'Additionally, users must have an email address within one of the following  '
                                         f'domains: {self.valid_sync_email_domains}. '
                                         "Users with emails of other domains are out of AD's server scope "
                                         'and their information cannot be retrieved through AD LDAP lookups. '
                                         'Any FreeIPA user not found in AD will automatically be considered terminated '
                                         "and will be deleted and moved to the 'preserved users' group. "
                                         "Admins can re-enable preserved users from FreeIPA's Web GUI, but will need "
                                         'to reconfigure their aliases, groups and password. '
                                         'Terminated users not tracked in AD are not evaluated by this function and '
                                         'will need to be deleted manually. '
                                         "The system's 'admin' user will never be deleted automatically and can always "
                                         'be used for FreeIPA access in emergency situations. '
                                         f'This option is designed to be run on an cronjob every {self.cache_validity} '
                                         'minutes to automate the handling of user terminations',
                                    action='store_true')

        main_functions.add_argument('-p', '--remind-password-change',
                                    help='sends notification email to existing users using the default password asking '
                                         'them to change it. '
                                         'When a user password is set or reset by and admin for the first time, users '
                                         "are prompt to change it the first time they log into FreeIPA's Web GUI. "
                                         'However, users will still be able to use the temporary password on LDAP '
                                         "based applications such as TACACS and RADIUS because FreeIPA's LDAP server "
                                         'will not distinguish expired or reset users when accepting credentials.'
                                         'This program option identifies who has not changed the password comparing '
                                         'the password expiration and password last changed FreeIPA user fields. '
                                         'Users that have not changed the passwords will have both fields set with the '
                                         'same value',
                                    action='store_true')

        output_level = argparser.add_mutually_exclusive_group()

        output_level.add_argument('-q', '--quiet',
                                  help='hides all the terminal outputs',
                                  default=False,
                                  action='store_true')

        output_level.add_argument('-v', '--verbose',
                                  help='prints the content of the log file to the CLI upon program execution. '
                                       'By the default, the program stores WARNING and ERROR log messages at '
                                       f'{self.log_file}. '
                                       'The level of detail documented in the log can be modified with the -y '
                                       '(--info-log-level) and -z (--debug-log-level) options',
                                  action='store_true')

        log_levels = argparser.add_mutually_exclusive_group()

        log_levels.add_argument('-y', '--info-log-level',
                                help='updates the application log level to record INFO message types. '
                                     'This is useful for getting a step-by-step summary of the logic followed by the '
                                     'program. '
                                     f"The log is stored at {self.log_file} and can also be printed in terminal during "
                                     'execution using the -v (--verbose) option',
                                action='store_true')

        log_levels.add_argument('-z', '--debug-log-level',
                                help='updates the application log level to record DEBUG message types. '
                                     'This is useful for getting highly detailed information of what the application '
                                     'does. '
                                     f"The log is stored at {self.log_file} and can also be printed in terminal during "
                                     'execution using the -v (--verbose) option',
                                action='store_true')

        return argparser, argparser.parse_args()
