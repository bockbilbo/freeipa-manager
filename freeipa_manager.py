#!/usr/bin/env python3
#
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

import os
from argparse import Namespace

from utils.utils import Utils


def app_option_check_cache(app_utils: Utils, quiet: bool) -> None:
    status = app_utils.get_cache_handler().is_cache_outdated()

    if status and not quiet:
        print('Cache is outdated')
    elif not status and not quiet:
        print('Cache is up-to-date')


def app_option_check_servers(app_utils: Utils, quiet: bool) -> None:
    ad_reachable, freeipa_reachable, smtp_reachable = app_utils.check_server_connectivity()

    if ad_reachable == freeipa_reachable == smtp_reachable is True and not quiet:
        print('FreeIPA, AD and SMTP servers are reachable')
    elif not quiet:
        if not ad_reachable:
            print('AD server is not reachable')
        if not freeipa_reachable:
            print('FreeIPA server is not reachable')
        if not smtp_reachable:
            print('SMTP server is not reachable')


def app_option_delete_cache(app_utils: Utils, quiet: bool) -> None:
    status = app_utils.get_cache_handler().delete_cache()

    if status and not quiet:
        print('Cache files have been deleted')
    elif not quiet:
        print('Cache files were not deleted because they do not exist')


def app_option_delete_user(user_id: str, app_utils: Utils, quiet: bool) -> None:
    status = app_utils.get_freeipa_handler().delete_freeipa_user(user_id)

    if status and not quiet:
        print(f'User {user_id} deleted successfully')
    elif not quiet:
        print(f'User {user_id} could not be deleted')


def app_option_delete_user_otp_tokens(user_id: str, app_utils: Utils, quiet: bool) -> None:
    status = app_utils.get_freeipa_handler().delete_freeipa_user_otp_tokens(user_id)

    if status and not quiet:
        print(f'OTP token(s) removed for user {user_id}')
    elif not quiet:
        print(f'OTP token(s) could not be removed for user {user_id}')


def app_option_disable_user(user_id: str, app_utils: Utils, quiet: bool) -> None:
    status = app_utils.get_freeipa_handler().disable_freeipa_user(user_id)

    if status and not quiet:
        print(f'User {user_id} disabled successfully')
    elif not quiet:
        print(f'User {user_id} could not be disabled')


def app_option_enable_user(user_id: str, app_utils: Utils, quiet: bool) -> None:
    status = app_utils.get_freeipa_handler().enable_freeipa_user(user_id)

    if status and not quiet:
        print(f'User {user_id} enabled successfully')
    elif not quiet:
        print(f'User {user_id} could not be enabled')


def app_option_export_file(export_file: str, app_utils: Utils, quiet: bool) -> None:
    if export_file and export_file[:1] not in ['.', '/']:
        export_file = os.getcwd() + '/' + export_file
    elif not export_file:
        export_file = os.getcwd() + '/' + app_utils.get_csv_files()['export_file']

    status = app_utils.get_freeipa_handler().export_to_csv(export_file)

    if status and not quiet:
        print(f'FreeIPA users exported successfully to {export_file}')
    elif not quiet:
        print(f'FreeIPA users could not be exported to {export_file}')


def app_option_import_file(import_file: str, app_utils: Utils, quiet: bool) -> None:
    if import_file and import_file[:1] not in ['.', '/']:
        import_file = os.getcwd() + '/' + import_file
    elif not import_file:
        import_file = os.getcwd() + '/' + app_utils.get_csv_files()['import_file']

    imported_users, updated_users, skipped_users, not_imported_users = app_utils.import_csv(import_file)

    if imported_users and not quiet:
        print('The following users were imported to FreeIPA:')
        for user in imported_users:
            print(f"   - {user} with temporary password '{imported_users[user]}'")

    if updated_users and not quiet:
        print('The following users were updated in FreeIPA:')
        for user in updated_users:
            print(f'   - {user}')

    if skipped_users and not quiet:
        print('The following users required no update and were skipped:')
        for user in skipped_users:
            print(f'   - {user}')

    if not_imported_users and not quiet:
        print('The following users were not imported to FreeIPA due to errors:')
        for user in not_imported_users:
            print(f'   - {user}')

    if (imported_users or updated_users or skipped_users or not_imported_users) and not quiet:
        print('FreeIPA user import completed.')
    elif not quiet:
        print('No users to import at this time.')


def app_option_list_expired_users(app_utils: Utils, quiet: bool) -> None:
    expired_users, expired_users_disabled = app_utils.get_freeipa_handler().get_expired_users()

    if expired_users and not quiet:
        print('The passwords of the following users have expired within the last '
              f'{app_utils.get_password_gracious_period()} days:')
        for user_id in expired_users:
            print(f'  - {user_id}')

    if expired_users_disabled and not quiet:
        print('The following user accounts have been disabled for not changing their password within '
              f'{app_utils.get_password_gracious_period()} days after expiration:')
        for user_id in expired_users_disabled:
            print(f'  - {user_id}')

    if not expired_users and not expired_users_disabled and not quiet:
        print('There are no expired users at this time')


def app_option_list_users_no_password(app_utils: Utils, quiet: bool) -> None:

    users_no_password = app_utils.get_freeipa_handler().get_users_no_password()

    if users_no_password and not quiet:
        print('The following users must change their password: ')
        for user_id in users_no_password:
            print(f'  - {user_id}')
    elif not quiet:
        print('There are no users pending password change at this time')


def app_option_process_password_expirations(app_utils: Utils, quiet: bool) -> None:
    notified, expired, disabled = app_utils.process_password_expirations()

    if notified and not quiet:
        print('The following users were notified for upcoming password expiration:')
        for user in notified:
            print(f'   - {user}')
    elif not quiet:
        print('No user password expiration reminders to send at this time')

    if expired and not quiet:
        print('Passwords for the following users have expired:')
        for user in expired:
            print(f'   - {user}')

    if disabled and not quiet:
        print('The following users were disabled for not changing their passwords within '
              f'the gracious period of {app_utils.get_password_gracious_period()} days:')
        for user in disabled:
            print(f'   - {user}')

    if not notified and not expired and not disabled and not quiet:
        print('No upcoming password expirations or expired users found.')


def app_option_process_terminated_users(app_utils: Utils, quiet: bool) -> None:
    deleted_users, not_deleted_users = app_utils.delete_terminated_users()

    if deleted_users and not quiet:
        print(f'The following terminated users were deleted from FreeIPA:')
        for user in deleted_users:
            print(f'   - {user}')

    if not_deleted_users and not quiet:
        print('The following terminated users could not be deleted from FreeIPA:')
        for user in not_deleted_users:
            print(f'   - {user}')

    if not deleted_users and not not_deleted_users and not quiet:
        print('No terminated users identified at this time')


def add_option_remind_password_change(app_utils: Utils, quiet: bool) -> None:
    status, users_no_password = app_utils.remind_password_change()

    if status and not quiet:
        print('The following users have been notified to change their passwords: ')
        for user in users_no_password:
            print(f'   - {user}')

    elif not quiet:
        print('No user found to be notified for password change')


def app_option_reset_user_password(user_id: str, app_utils: Utils, quiet: bool) -> None:
    success, password = app_utils.reset_user_password(user_id)

    if success and not quiet:
        print(f"Password for user {user_id} successfully changed to '{password}', user notified")

    elif not quiet:
        print(f'Password could not be changed for user {user_id}')


def app_option_template_file(template_file: str, app_utils: Utils, quiet: bool) -> None:
    if template_file and template_file[:1] not in ['.', '/']:
        template_file = os.getcwd() + '/' + template_file
    elif not template_file:
        template_file = os.getcwd() + '/' + app_utils.get_csv_files()['import_template']

    status = app_utils.get_freeipa_handler().create_csv_template(template_file)

    if status and not quiet:
        print(f'Import CSV template successfully created at {template_file}')
    elif not quiet:
        print(f'Could not create the CSV template file at {template_file}')


def app_option_update_ad_cache(app_utils: Utils, quiet: bool) -> None:
    ad_users = app_utils.get_ad_handler().get_ad_users(force_update_cache=True)

    if ad_users and not quiet:
        print('AD user cache has been updated')
    elif not ad_users and not quiet:
        print('AD user cache could not be updated')


def app_option_update_cache_files(app_utils: Utils, quiet: bool) -> None:
    ad_users = app_utils.get_ad_handler().get_ad_users(force_update_cache=True)
    freeipa_users = app_utils.get_freeipa_handler().get_freeipa_users(force_update_cache=True)

    if ad_users and freeipa_users and not quiet:
        print('FreeIPA and AD user caches have been updated')
    elif ad_users and not quiet:
        print('AD users cache has been updated but could not update the FreeIPA cache')
    elif freeipa_users and not quiet:
        print('FreeIPA users cache has been updated but could not update the AD cache')
    elif not quiet:
        print('FreeIPA and AD user cache files could not be updated')


def app_option_update_freeipa_cache(app_utils: Utils, quiet: bool) -> None:
    freeipa_users = app_utils.get_freeipa_handler().get_freeipa_users(force_update_cache=True)

    if freeipa_users and not quiet:
        print('FreeIPA user cache has been updated')
    elif not freeipa_users and not quiet:
        print('FreeIPA user cache could not be updated')


def app_option_update_from_ad(app_utils: Utils, quiet: bool) -> None:
    updates_success, updates_unsuccessful = app_utils.update_user_data_from_ad()

    if updates_success and not quiet:
        print('The following users were updated:')
        for user in updates_success:
            print(f'   - {user}')

    if updates_unsuccessful and not quiet:
        print('The following users could not be updated: ')
        for user in updates_unsuccessful:
            print(f'   - {user}')

    if not updates_success and not updates_unsuccessful and not quiet:
        print('No users to update at this time')


def check_for_logging_args(app_utils: Utils, args: Namespace) -> None:
    logger = app_utils.get_logger()

    if args.verbose:
        logger.enable_verbose()

    if args.info_log_level:
        logger.set_level_info()
    elif args.debug_log_level:
        logger.set_level_debug()


if __name__ == "__main__":
    valid_environment = False
    config_file = os.path.dirname(os.path.realpath(__file__)) + '/config.yaml'

    if os.path.isfile(config_file):
        utils = Utils(config_file)
        parser, cli_args = utils.get_menu().generate_menu()

        if utils.validate_running_environment(cli_args.check_servers):
            valid_environment = True

            check_for_logging_args(utils, cli_args)

            if cli_args.check_servers:
                app_option_check_servers(utils, cli_args.quiet)

            elif cli_args.check_cache:
                app_option_check_cache(utils, cli_args.quiet)

            elif cli_args.update_ad_cache:
                app_option_update_ad_cache(utils, cli_args.quiet)

            elif cli_args.update_freeipa_cache:
                app_option_update_freeipa_cache(utils, cli_args.quiet)

            elif cli_args.update_cache_files:
                app_option_update_cache_files(utils, cli_args.quiet)

            elif cli_args.delete_cache:
                app_option_delete_cache(utils, cli_args.quiet)

            elif cli_args.list_expired_users:
                app_option_list_expired_users(utils, cli_args.quiet)

            elif cli_args.list_users_no_password:
                app_option_list_users_no_password(utils, cli_args.quiet)

            elif cli_args.disable_user:
                app_option_disable_user(cli_args.disable_user.lower().strip(), utils, cli_args.quiet)

            elif cli_args.enable_user:
                app_option_enable_user(cli_args.enable_user.lower().strip(), utils, cli_args.quiet)

            elif cli_args.delete_user:
                app_option_delete_user(cli_args.delete_user.lower().strip(), utils, cli_args.quiet)

            elif cli_args.delete_user_otp_tokens:
                app_option_delete_user_otp_tokens(cli_args.delete_user_otp_tokens.lower().strip(), utils,
                                                  cli_args.quiet)

            elif cli_args.reset_user_password:
                app_option_reset_user_password(cli_args.reset_user_password.lower().strip(), utils, cli_args.quiet)

            elif cli_args.export_file is not None:
                app_option_export_file(cli_args.export_file.lower().strip(), utils, cli_args.quiet)

            elif cli_args.import_file is not None:
                app_option_import_file(cli_args.import_file.lower().strip(), utils, cli_args.quiet)

            elif cli_args.template_file is not None:
                app_option_template_file(cli_args.template_file.lower().strip(), utils, cli_args.quiet)

            elif cli_args.update_from_ad:
                app_option_update_from_ad(utils, cli_args.quiet)

            elif cli_args.process_password_expirations:
                app_option_process_password_expirations(utils, cli_args.quiet)

            elif cli_args.process_terminated_users:
                app_option_process_terminated_users(utils, cli_args.quiet)

            elif cli_args.remind_password_change:
                add_option_remind_password_change(utils, cli_args.quiet)

            else:
                parser.print_help()

    if not valid_environment:
        print('The program is missing required files or server connectivity to run and cannot be executed')
