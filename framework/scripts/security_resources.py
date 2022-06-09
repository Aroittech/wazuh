# Copyright (C) 2015, Wazuh Inc.
# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is free software; you can redistribute it and/or modify it under the terms of GPLv2

import argparse
import asyncio
import sys
from os.path import join

try:
    from wazuh import WazuhError
    from wazuh.core.results import AffectedItemsWazuhResult
    from wazuh.core.cluster import utils as cluster_utils
except Exception as e:
    print("Error importing 'Wazuh' package.\n\n{0}\n".format(e))
    exit()


async def restore_default_passwords():
    """Try to update all RBAC default users passwords with console prompt."""
    import yaml
    from getpass import getpass
    from wazuh.core.common import DEFAULT_RBAC_RESOURCES
    from wazuh.security import update_user

    default_users_file = join(DEFAULT_RBAC_RESOURCES, 'users.yaml')
    with open(default_users_file) as f:
        users = yaml.safe_load(f)

    results = {}
    for user_id, username in enumerate(users['default_users']):
        new_password = getpass(f"New password for '{username}' (skip): ")
        if new_password == "":
            continue

        response = await cluster_utils.forward_function(update_user, f_kwargs={'user_id': str(user_id + 1),
                                                                               'password': new_password})

        results[username] = f'FAILED | {str(response)}' if isinstance(response, Exception) else 'UPDATED'

    for user, status in results.items():
        print(f"\t{user}: {status}")


async def reset_rbac_database():
    """Attempt to fully wipe the RBAC database to restore factory values. Input confirmation is required."""
    if input('This action will completely wipe your RBAC configuration and restart it to default values. Type '
             'RESET to proceed: ') != 'RESET':
        print('RBAC database reset aborted.')
        sys.exit(0)

    from wazuh.core.security import rbac_db_factory_reset

    response = await cluster_utils.forward_function(rbac_db_factory_reset)

    print(f'RBAC database reset failed | {str(response)}' if isinstance(response, Exception)
          else '\tSuccessfully reset RBAC database')


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Wazuh RBAC manager",
                                         usage=
                                         "Change admin users passwords\n\n"
                                         "--change-passwords\n\n"
                                         "Reset RBAC database\n\n"
                                         "--factory-reset"
                                         )
    arg_parser.add_argument("--change-passwords", action='store_true', dest='change_passwords',
                            help="Change the password for each default user. Empty values will leave the password "
                                 "unchanged.")
    arg_parser.add_argument("--factory-reset", action='store_true', dest='factory_reset',
                            help="Restart the RBAC database to its default state. This will completely wipe your custom"
                                 " RBAC information.")
    args = arg_parser.parse_args()

    if not len(sys.argv) > 1:
        arg_parser.print_help()
        sys.exit(0)

    try:
        if args.change_passwords:
            asyncio.run(restore_default_passwords())
            sys.exit(0)
        elif args.factory_reset:
            asyncio.run(reset_rbac_database())
            sys.exit(0)
    except WazuhError as e:
        print(f"Error {e.code}: {e.message}")
    except Exception as e:
        print(f"Internal error: {e}")
