# FreeIPA Manager

## About:

FreeIPA Manager is a program conceived to facilitate user management in [FreeIPA](https://www.freeipa.org/page/Main_Page "FreeIPA"),
offering batch user imports and updates, user synchronization with an external Active Directory server, or password expiration email notifications among other things.

Read the program options below for more information on the available features.

## System Requirements

* A FreeIPA server - *to manage user accounts from*
* A Debian or Red Hat based server - *for running the application*
* A Windows AD server - *for user synchronization*
* An SMTP relay server - *for email notifications*

## Installation

The following steps will install the program inside */opt/freeipa_manager/*, creating a symbolink link within the system path at */usr/sbin/freeipa_manager*:

1. Download the code from the repository:
```bash
git clone https://github.com/bockbilbo/freeipa-manager.git
cd freeipa-manager
```

2. Install system dependencies:
```bash
sudo make install-system-dependencies
```

3. Install the program:
```bash
sudo make install
```

## Uninstallation

Run the following from the location of the Makefile file:

```bash
sudo make uninstall
```

Alternatively, you can manually delete the files with:

```bash
sudo rm -Rf /opt/freeipa_manager
sudo rm /usr/sbin/freeipa_manager
```

## Configuration

Modify [*/opt/freeipa_manager/config.yaml* ](https://github.com/bockbilbo/freeipa-manager/blob/main/config.yaml "*/opt/freeipa_manager/config.yaml* ")with your desired settings before running the program. The YAML file has comments explaining how to edit it.

## Crontab

Feel free to add the following jobs to your server's crontab for processing terminated users, synchronizing users with Windows Active Directory and handling password expirations automatically.

This could be placed inside */etc/cron.d/freeipa_manager:*
```
# Process terminated employees:
0 * * * * root  /usr/sbin/freeipa_manager -ql >/dev/null 2>&1
# Synchronize user data from AD:
15 * * * * root  /usr/sbin/freeipa_manager -qu >/dev/null 2>&1
# Process password expirations:
0 2 * * * root  /usr/sbin/freeipa_manager -qk >/dev/null 2>&1
```

## Execution

Run *freeipa_manager* from the your server shell appending the desired arguments based on the following:

```
[user@server ~]$ freeipa_manager -h
usage: freeipa_manager [-h]
                       (-s | -b | -a | -f | -c | -g | -d USER_ID | -e USER_ID | -w USER_ID | -o USER_ID | -r USER_ID | -m | -n | -x [FILE_PATH] | -i [FILE_PATH] | -t [FILE_PATH] | -u | -k | -l | -p)
                       [-q | -v] [-y | -z]

FreeIPA Manager is a program conceived to facilitate user management in
FreeIPA, offering batch user imports and updates, user synchronization with
Active Directory or password expiration email notifications among other
things. Read the help output below to understand all the options available.

optional arguments:
  -h, --help            show this help message and exit
  -s, --check-servers   checks the reachability of the SMTP, FreeIPA and AD
                        servers performing a simple TCP port analysis for
                        SMTP, HTTPS and LDAPS. The program will always check
                        the availability of the servers upon execution, but
                        this option is useful for quick health checks
  -b, --check-cache     checks the status of the FreeIPA and AD user cache.The
                        cache is only valid for 60 minutes and it is stored in
                        JSON files located at /opt/freeipa_manager/cache.
                        Direct queries to the servers usually add a handful of
                        seconds to the program execution time, hence the
                        reason for caching. The program will automatically
                        update the cache if not available or expired and this
                        option is useful for quick health checks
  -a, --update-ad-cache
                        updates the local AD user cache stored at
                        /opt/freeipa_manager/cache/ad_users.json. This cache
                        is updated automatically when the file is missing or
                        upon cache expiration after 60 minutes. Caching the AD
                        user database reduces the program execution time and
                        manual cache updates should not be required unless you
                        are aware of a recent AD change needed for an
                        import/update/sync task
  -f, --update-freeipa-cache
                        updates the local FreeIPA user cache stored at
                        /opt/freeipa_manager/cache/freeipa_users.json. This
                        cache is updated automatically when the file is
                        missing, upon cache expiration after 60 minutes and
                        when performing database update tasks like adding,
                        modifying, disabling, enabling, deleting, or
                        synchronizing user accounts. The FreeIPA user cache
                        reduces the program execution time and manual cache
                        updates should not be required unless you are aware of
                        a recent FreeIPA DB change needed for an
                        import/update/sync task
  -c, --update-cache-files
                        updates both the local AD and FreeIPA user caches
                        stored at at /opt/freeipa_manager/cache/ad_users.json
                        and /opt/freeipa_manager/cache/freeipa_users.json.
                        Read the option descriptions of -a (--update-ad-cache)
                        and -f (--update-freeipa-cache) for more information
                        on caching
  -g, --delete-cache    deletes the local AD and FreeIPA user caches stored at
                        /opt/freeipa_manager/cache/ad_users.json and
                        /opt/freeipa_manager/cache/freeipa_users.json. This
                        option is useful when debugging the application and
                        should not be needed for normal operations. Use the -c
                        (--update-cache-files) option if you want to renew the
                        local cache
  -d USER_ID, --disable-user USER_ID
                        disables the user provided in the argument. The given
                        user name must use the dotted user_id format,
                        following the first.lastname naming convention used
                        for corporate email addresses. Disabled users maintain
                        their group memberships and aliases, and can be re-
                        enabled from command line with the -e (--enable-user)
                        option . Admins can also disable users from FreeIPA's
                        web GUI directly
  -e USER_ID, --enable-user USER_ID
                        enables the user provided in the argument. The given
                        user name must use the dotted user_id format,
                        following the first.lastname naming convention used
                        for corporate email addresses. Admins can also enable
                        users from FreeIPA's web GUI directly
  -w USER_ID, --delete-user USER_ID
                        deletes the user provided in the argument. The given
                        user name must use the dotted user_id format,
                        following the first.lastname naming convention used
                        for corporate email addresses. Deleted users are
                        automatically disabled, moved to the 'preserved users'
                        group, and can only be re-enabled using the FreeIPA
                        Web GUI. Keep in mind that when users are deleted and
                        moved to the preserved status, they lose their user
                        groups, alias information and password. These will
                        need to be re-configured manually from the Web GUI
                        upon user re-activation
  -o USER_ID, --delete-user-otp-tokens USER_ID
                        deletes all the OTP tokens linked with the user
                        provided in the argument. The given user name must use
                        the dotted user_id format, following the
                        first.lastname naming convention used for corporate
                        email addresses. When FreeIPA users set OTP access
                        they must append 6 temporary digits generated by their
                        token to their passwords when using their accounts. If
                        users lose access to their tokens they will not be
                        able to access the system. This option is useful to
                        easily unlock users unable to use their accounts due
                        lost OTP tokens
  -r USER_ID, --reset-user-password USER_ID
                        resets the password for the user specified in the
                        argument and notifies the change. The given user name
                        must exist in the user database and must use the
                        dotted user_id format, following the first.lastname
                        naming convention used for corporate email addresses.
                        The program will obtain the user's email from the
                        FreeIPA database and send a notification prompting the
                        user to change the password. This option is useful to
                        quickly reset user passwords with using random
                        passwords
  -m, --list-expired-users
                        prints the list of users with expired passwords,
                        including the time past since expiration. Keep in mind
                        that expired users are not allowed to access servers
                        managed by FreeIPA, but still can use their
                        credentials for LDAP authentication, commonly used for
                        internal tools, TACACS and RADIUS. To restrict the
                        access of users in this scenario, the program will
                        disable users with passwords expired for more than the
                        gracious period of 14 days, forcing users to contact
                        support to restore their account. The evaluation of
                        expired users is performed when calling option -k
                        (--process-password-expirations)
  -n, --list-users-no-password
                        prints the list of users whose password was reset but
                        not changed, including users disabled for not changing
                        their password within the gracious period of 14 days
                        after expiration. This option is useful to get a quick
                        status of inactive users in order to to evaluate their
                        deletion from the system
  -x [FILE_PATH], --export-users [FILE_PATH]
                        exports the existing FreeIPA user database into the
                        CSV file specified by the argument. If no file path
                        given, the data export will be saved as
                        ./freeipa_user_export.csv. Keep in mind that the
                        exported data will exclude system users in FreeIPA,
                        only saving data of users belonging to the following
                        groups: user_group_1, user_group_2, user_group_3 and
                        user_group_4.
  -i [FILE_PATH], --import-users [FILE_PATH]
                        imports user data into FreeIPA from the CSV file
                        specified by the argument, creating or updating users
                        as needed. The user_id field is mandatory for both
                        actions and must match the user's corporate email
                        address user using the dotted format (i.e.
                        first.lastname). New users will need to have at least
                        an email, name, lastname and user_group populated upon
                        import. The user_group field must match one of the
                        following values: user_group_1, user_group_2,
                        user_group_3 and user_group_4. Keep in mind that users
                        can only belong to a single group. When updating the
                        group of an existing user, membership will be revoked
                        for its previous group. Additionally, if included, the
                        manager field must contain the user_id of the user's
                        manager, who must exist in the FreeIPA database. Keep
                        in mind that most of the data imported through this
                        option will be overwritten for users built in the AD
                        server upon server synchronization via the -u
                        (--update-from-ad) option. If no file path is provided
                        as an argument, the script will attempt to load import
                        data from ./import_data.csv
  -t [FILE_PATH], --import-template [FILE_PATH]
                        creates an empty CSV template file at at the given
                        location to be used for user imports with the -i
                        (--import-users) option. If no file path is provided
                        as an argument, the program will attempt tocreate the
                        template at ./import_template.csv
  -u, --update-from-ad  updates the existing FreeIPA user data with
                        information available from AD. The program will
                        compare users one by one, prioritizing AD information
                        for those with an email address in one of the
                        following domains: mycompany.com and mybrandname.com.
                        Users with emails of other domains are out of the AD
                        server scope and their information cannot be retrieved
                        through AD LDAP lookups. Additionally, synchronization
                        will be restricted only to FreeIPA users belonging to
                        the following groups: user_group_1, user_group_2,
                        user_group_3 and user_group_4. During synchronization,
                        the following FreeIPA user fields will be overwritten if
                        a different -not empty- value is found on AD: email
                        address, name, last name, full name, job title, street
                        address, city state, zip code, department, employee
                        number, employee type, preferred language, phone
                        number and manager -if exists in FreeIPA
  -k, --process-password-expirations
                        reviews the password expiration dates for all the
                        existing FreeIPA users, notifies users close to
                        expiration and disables those whose password has been
                        expired over the gracious period of 14 days. Password
                        reset reminders are sent to those with passwords set
                        to expire in the next 14, 7, 3 and 1 days. Notified
                        users are logged in a local cache located at
                        /opt/freeipa_manager/cache/freeipa_users.json to
                        prevent spamming. Keep in mind that used password
                        policies might differ between existing user groups
                        depending on FreeIPA's configuration. Policies define
                        rules for passwords such as the maximum lifetime,
                        history size, character types or length. Password
                        policies can be reviewed and modified by admins from
                        FreeIPA's Web GUI at Policy -> Password Policies. The
                        -k (--process-password-expirations) option is designed
                        to be run on a daily cronjob to automate notifications
  -l, --process-terminated-users
                        compares the FreeAIPA users against AD and deletes
                        terminated users from the database. User termination
                        evaluation is performed based on the user's group and
                        email domain.A user must belong to any of the
                        following groups in order to be evaluated for
                        termination: user_group_1, user_group_2, user_group_3
                        and user_group_4. Additionally, users must have
                        an email address within one of the following domains:
                        mycompany.com and mybrandname.com. Users with emails of
                        other domains are out of AD's server scope and their
                        information cannot be retrieved through AD LDAP lookups.
                        Any FreeIPA user not found in AD will automatically be
                        considered terminated and will be deleted and moved to
                        the 'preserved users' group. Admins can re-enable
                        preserved users from FreeIPA's Web GUI, but will need to
                        reconfigure their aliases, groups and password.
                        Terminated users not tracked in AD are not evaluated by
                        this function and will need to be deleted manually. The
                        system's 'admin' user will never be deleted
                        automatically and can always be used for FreeIPA access
                        in emergency situations. This option is designed to be
                        run on an cronjob every 60 minutes to automate the
                        handling of user terminations
  -p, --remind-password-change
                        sends notification email to existing users using the
                        default password asking them to change it. When a user
                        password is set or reset by and admin for the first
                        time, users are prompt to change it the first time
                        they log into FreeIPA's Web GUI. However, users will
                        still be able to use the temporary password on LDAP
                        based applications such as TACACS and RADIUS because
                        FreeIPA's LDAP server will not distinguish expired or
                        reset users when accepting credentials.This program
                        option identifies who has not changed the password
                        comparing the password expiration and password last
                        changed FreeIPA user fields. Users that have not
                        changed the passwords will have both fields set with
                        the same value
  -q, --quiet           hides all the terminal outputs
  -v, --verbose         prints the content of the log file to the CLI upon
                        program execution. By the default, the program stores
                        WARNING and ERROR log messages at
                        /opt/freeipa_manager/application.log. The level of
                        detail documented in the log can be modified with the
                        -y (--info-log-level) and -z (--debug-log-level)
                        options
  -y, --info-log-level  updates the application log level to record INFO
                        message types. This is useful for getting a step-by-
                        step summary of the logic followed by the program. The
                        log is stored at /opt/freeipa_manager/application.log
                        and can also be printed in terminal during execution
                        using the -v (--verbose) option
  -z, --debug-log-level
                        updates the application log level to record DEBUG
                        message types. This is useful for getting highly
                        detailed information of what the application does. The
                        log is stored at /opt/freeipa_manager/application.log
                        and can also be printed in terminal during execution
                        using the -v (--verbose) option
```
