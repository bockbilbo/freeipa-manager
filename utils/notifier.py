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
import logging
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid as create_msgid

import html2text


class Notifier:

    def __init__(self, smtp_relay_server: str, from_email: str, admin_emails: str, template_files: dict,
                 password_gracious_period: int):
        self.log = logging.getLogger('freeipa_manager')
        self.smtp_relay_server = smtp_relay_server
        self.from_email = from_email
        self.admin_emails = admin_emails
        self.template_files = template_files
        self.password_gracious_period = password_gracious_period

    @staticmethod
    def __get_alias_p(user_id: str, alias: str) -> str:
        if user_id and alias:
            return '<p style="margin: 0; line-height: 1.2; word-break: break-word ; mso-line-height-alt: 17px; margin' \
                   '-top: 0; margin-bottom: 0;">After you change your password, you will be able to use the new crede' \
                   f"ntials to access our network devices. To make things easier, you will be able to use '{user_id}'" \
                   f" and '{alias}' as your username with the same password when using the CLI.</p><p style='margin: " \
                   '0; line-height: 1.2; word-break: break-word; mso-line-height-alt: 17px; margin-top: 0; margin-bot' \
                   "tom: 0;'> </p>"
        elif user_id:
            return '<p style="margin: 0; line-height: 1.2; word-break: break-word ; mso-line-height-alt: 17px; margin' \
                   '-top: 0; margin-bottom: 0;">After you change your password, you will be able to use the new crede' \
                   f"ntials to access our network devices.</p><p style='margin: 0; line-height: 1.2; word-break: brea" \
                   "k-word; mso-line-height-alt: 17px; margin-top: 0; margin-bottom: 0;'> </p>"
        else:
            return ''

    @staticmethod
    def __get_list_div(div_text: str, disabled_users_li: str) -> str:
        if div_text and disabled_users_li:
            return '<div style="color:#555555;font-family:Arial, Helvetica Neue, Helvetica, sans-serif;line-height:1.' \
                   '2;padding-top:0px;padding-right:10px;padding-bottom:10px;padding-left:10px;"><div class="txtTinyM' \
                   'ce-wrapper" style="font-size: 14px; line-height: 1.2; color: #555555; font-family: Arial, Helveti' \
                   'ca Neue, Helvetica, sans-serif; mso-line-height-alt: 17px;"><p style="margin: 0; line-height: 1.2' \
                   f';word-break: break-word; mso-line-height-alt: 17px; margin-top: 0; margin-bottom: 0;">{div_text}' \
                   '</p></div></div><div style="color:#555555;font-family:Arial, Helvetica Neue, Helvetica, sans-seri' \
                   'f;line-height:1.2;padding-top:0px;padding-right:10px;padding-bottom:10px;padding-left:10px;"><div' \
                   ' class="txtTinyMce-wrapper" style="font-size: 14px; line-height: 1.2; color: #555555; font-family' \
                   f':Arial, Helvetica Neue, Helvetica, sans-serif;mso-line-height-alt:17px;"><ul>{disabled_users_li}' \
                   '</ul></div></div>'
        else:
            return ''

    @staticmethod
    def __get_template_li(list_text: str) -> str:

        return f'<li style="line-height: 1.2; mso-line-height-alt: NaNpx;">{list_text}</li>'

    def __send_email(self, email_sender, email_recipients, subject, template_name, template_fields) -> bool:

        self.log.debug(f'Sending email based on template {template_name}')

        msg = EmailMessage()

        msg['From'] = email_sender
        msg['To'] = email_recipients
        msg['Subject'] = subject

        try:
            with open(self.template_files[template_name], 'r') as template:
                html_body = template.read().replace('\n', '')

            h = html2text.HTML2Text()
            h.ignore_links = True
            h.ignore_images = True
            h.ignore_emphasis = True
            h.ignore_anchors = True
            h.ignore_tables = True

            company_logo_cid = create_msgid()

            plain_body = h.handle(html_body.format(company_logo_cid=company_logo_cid[1:-1], **template_fields))

            msg.set_content(plain_body)

            msg.add_alternative(html_body.format(company_logo_cid=company_logo_cid[1:-1],
                                                 **template_fields), subtype='html')

            with open(self.template_files['company_logo'], 'rb') as img:
                msg.get_payload()[1].add_related(img.read(), 'image', 'png', cid=company_logo_cid)

            with smtplib.SMTP(self.smtp_relay_server) as s:
                s.send_message(msg)
                self.log.debug('Email sent successfully')
                s.quit()

            return True

        except (OSError, smtplib.SMTPException) as e:
            self.log.error(f'Email could not be sent: {e}')
            return False

    def notify_expiration(self, user_id: str, email: str, name: str, days_to_expiration: int,
                          expiration_date: datetime.date) -> bool:

        self.log.debug(f'Sending password expiration reminder to user {user_id}')

        template = 'notify_expiration'
        subject = "Your credentials to access the company network are expiring soon"
        template_fields = {'user_id': user_id,
                           'name': name,
                           'days_left': days_to_expiration,
                           'expiration_date': expiration_date.strftime('%A, %B %d, %Y')}

        return self.__send_email(self.from_email, email, subject, template, template_fields)

    def notify_new_account(self, user_id: str, alias: str, name: str, email: str, password: str) -> bool:

        template = 'notify_new_account'
        subject = "Your new credentials to access the company network are ready"
        template_fields = {'user_id': user_id,
                           'name': name,
                           'password': password,
                           'alias': self.__get_alias_p(user_id, alias)}

        return self.__send_email(self.from_email, email, subject, template, template_fields)

    def notify_password_reset(self, user_id: str, alias: str, name: str, email: str, password: str) -> bool:

        template = 'notify_passwd_reset'
        subject = "Your credentials to access the company network have been reset"
        template_fields = {'user_id': user_id,
                           'name': name,
                           'password': password,
                           'alias': self.__get_alias_p(user_id, alias)}

        return self.__send_email(self.from_email, email, subject, template, template_fields)

    def remind_password_reset(self, user_id: str, alias: str, name: str, email: str) -> bool:

        template = 'remind_passwd_reset'
        subject = 'Please, change your company network password now'
        template_fields = {'user_id': user_id,
                           'name': name,
                           'alias': self.__get_alias_p(user_id, alias)}

        return self.__send_email(self.from_email, email, subject, template, template_fields)

    def report_ad_updates(self, updated_users_list: list) -> bool:

        template = 'report_ad_updates'
        recipients = self.admin_emails
        subject = f"FreeIPA AD Synchronization Update Report for {datetime.datetime.now().date().strftime('%m/%d/%Y')}"

        updated_users = ''
        for user in updated_users_list:
            updated_users = updated_users + self.__get_template_li(user)

        template_fields = {'updated_users': updated_users}

        return self.__send_email(self.from_email, recipients, subject, template, template_fields)

    def report_expirations(self, expired_users_list: list, expired_users_to_disable_list: list) -> bool:

        self.log.debug('Sending password expiration report to admins')

        template = 'report_expirations'
        recipients = self.admin_emails
        subject = f"Password expiration report for {datetime.datetime.now().date().strftime('%m/%d/%Y')}"

        expired_users_li = ''
        if expired_users_list:
            for user in expired_users_list:
                expired_users_li = expired_users_li + self.__get_template_li(user)

        disabled_users_li = ''
        if expired_users_to_disable_list:
            for user in expired_users_to_disable_list:
                disabled_users_li = disabled_users_li + self.__get_template_li(user)

        intro_text = ''
        first_list = ''
        additional_block = ''

        if expired_users_li:
            intro_text = 'The passwords for the following users have expired:'
            first_list = expired_users_li
            if disabled_users_li:
                div_text = 'Additionally, the following users with passwords expired over the gracious period of ' \
                           f'{self.password_gracious_period} days have been disabled:'
                additional_block = self.__get_list_div(div_text, disabled_users_li)

        elif disabled_users_li:
            intro_text = 'The following users with passwords expired over the gracious period of ' \
                         f'{self.password_gracious_period} days have been disabled:'
            first_list = disabled_users_li

        template_fields = {'intro_text': intro_text,
                           'first_list': first_list,
                           'additional_block': additional_block}

        if expired_users_li or disabled_users_li:
            return self.__send_email(self.from_email, recipients, subject, template, template_fields)
        else:
            return False

    def report_terminated(self, deleted_users_list: list, not_deleted_users_list: list) -> bool:

        template = 'report_terminated'
        recipients = self.admin_emails
        subject = f"User Termination Report for {datetime.datetime.now().date().strftime('%m/%d/%Y')}"

        deleted_users = ''
        for user in deleted_users_list:
            deleted_users = deleted_users + self.__get_template_li(user)

        not_deleted_users = ''

        if not_deleted_users_list:

            not_deleted_users_li = ''
            for user in not_deleted_users_list:
                not_deleted_users_li = not_deleted_users_li + self.__get_template_li(user)

                not_deleted_users = \
                    '<div style="color:#555555; font-family:Arial, Helvetica Neue, Helvetica, sans-serif;line-height:' \
                    '1.2;padding-top:10px;padding-right:10px; padding-bottom:10px;padding-left:10px;"><div class="txt' \
                    'TinyMce-wrapper" style="font-size: 14px; line-height: 1.2; color: #555555; font-family: Arial, H' \
                    'elvetica Neue, Helvetica, sans-serif; mso-line-height-alt: 17px;"><p style="margin: 0; line-heig' \
                    'ht: 1.2; word-break: break-word; mso-line-height-alt: 17px; margin-top: 0; margin-bottom: 0;">Ad' \
                    'ditionally, other terminated users were identified, but could not be removed from FreeIPA. Pleas' \
                    'e review them manually:</p></div></div><div style="color:#555555;font-family:Arial, Helvetica Ne' \
                    'ue, Helvetica, sans-serif;line-height:1.2;padding-top:0px;padding-right:10px;padding-bottom:10px' \
                    ';padding-left:10px;"><div class="txtTinyMce-wrapper" style="font-size: 14px; line-height: 1.2; c' \
                    'olor: #555555; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; mso-line-height-alt: 1' \
                    f'7px;"><ul>{not_deleted_users_li}</ul></div></div>'

        template_fields = {'deleted_users': deleted_users,
                           'not_deleted_users': not_deleted_users}

        return self.__send_email(self.from_email, recipients, subject, template, template_fields)
