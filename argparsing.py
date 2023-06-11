from os import environ, path, makedirs, path, listdir
import argparse, datetime, shutil, sys
import duo_client


banner = """\
          ____              __   _____                      _ __       
         / __ \__  ______  / /__/ ___/___  _______  _______(_) /___  __
        / /_/ / / / / __ \/ //_/\__ \/ _ \/ ___/ / / / ___/ / __/ / / /
       / ____/ /_/ / / / / ,<  ___/ /  __/ /__/ /_/ / /  / / /_/ /_/ / 
      /_/    \__,_/_/ /_/_/|_|/____/\___/\___/\__,_/_/  /_/\__/\__, /  
                                             PRESENTS         /____/  
                                    Duodu 🦤

                Perform a Duo Push Notification Campaign
        """

parser = argparse.ArgumentParser(
    prog='Duo Push Notification Tester',
    description='Sends push notifications to all specified users, staggered over the specified period of time',
)

user_pings_wait = parser.add_argument_group("user_pings_wait")
user_pings_wait.add_argument('-w', '--user-wait', type=int, default=60, help='The amount of time in seconds to wait between each push notification sent to a specific user. This time does not include the time taken to wait for the notification to timeout or for the user to deny it. Defaults to 60 seconds if --user-pings is >1') # number of users to ping at once
user_pings_wait.add_argument('-u', '--user-pings', type=int, default=1, help='The number of times to send a user a push notification in a row. Defaults to 1') # number of users to ping at once

parser.add_argument('-b', '--batch-size', type=int, default=1, help='The number of users to send push notifications to at once') # number of users to ping at once
parser.add_argument('-t', '--time-between', type=int, default=300, help='The amount of time in seconds to wait between each batch of push notifications') # defaults to 5 minutes

duo_keys = parser.add_argument_group("duo_keys")
duo_keys.add_argument('host', help="API host url. E.g. api-1234abcd.duosecurity.com")
duo_keys.add_argument('--admin-ikey', help="Admin API integration key") # integration key
duo_keys.add_argument('--admin-skey', help="Admin API secret key") # secret key
duo_keys.add_argument('--auth-ikey', help="Auth API integration key") # integration key
duo_keys.add_argument('--auth-skey', help="Auth API secret key") # secret key

output_exclusive = parser.add_mutually_exclusive_group(required=False)
output_exclusive.add_argument('-o', '--output-file', default=None, help='Full or relative path of the output file including name e.g. /results/results.csv. Defaults to results/result<datetime>.csv')
output_exclusive.add_argument('-f', '--resume-from-file', help="Path of file containing results of a previous campaign to use to resume sending push notifications to and updating.")
output_exclusive.add_argument('-r', '--resume-from-last', action='store_true', default=False, help="Resumes sending push notifications from the latest file produced in results folder at the root of this directory.")

parser.add_argument('-i', '--ignore-list', help='Path to file of list of emails of users to ignore.')
parser.add_argument('-l', '--user-list', help="Sends push notifications only to specified users in a provided file. Userlist format is either one of `email` or `email - phonenumber`. E.g. user-list.txt")
parser.add_argument('-p', '--push-text', default="Login", help="Text to display in push notification. Defaults to 'Login'.")
parser.add_argument('-g', '--by-groups', help="Send push notifications to all users in specified groups. Groups are separated by a comma e.g. \"group1, group2\"")

cmds = parser.add_argument_group("cmds")
cmds.add_argument('--list-groups', action="store_true", help="To be used alone, no other commands will be executed. Lists groups associate with a given endpoint. Requires the admin integration key and secret key.")
cmds.add_argument('--empty-results', action="store_true", help="To be used alone, no other commands will be executed. Deletes all files in the results folder.")


makedirs("results", exist_ok=True)

def parse_args():
    def check_env(key:str) -> str:
        """
        Checks if env var is set.

        :param key: env vr to check for
        :type key: str
        :return: value of the key
        :rtype: str
        """    
        try:
            var = environ[key.upper()]
        except KeyError:
            return True
        return False

    args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])

    if args.host is None:
        parser.error("Positional argument 'host' required.")

    if args.empty_results:
        i = input("Delete content of results folder? [y/N]")
        if i == "y":
            try:
                shutil.rmtree("results")
            except:
                parser.error("Unable to empty out results folder. Please sure sure no files are open.")
            makedirs("results", exist_ok=True)
        exit()

    if args.admin_ikey is None and check_env("admin_ikey"):
        parser.error("--", args.admin_ikey.replace("_", "-"),"was not provided and isn't in environment variables. Please specify at least one.")

    if args.admin_skey is None and check_env("admin_skey"):
        parser.error("--", args.admin_skey.replace("_", "-"),"was not provided and isn't in environment variables. Please specify at least one.")

    if args.auth_ikey is None and check_env("auth_ikey"):
        parser.error("--", args.auth_ikey.replace("_", "-"),"was not provided and isn't in environment variables. Please specify at least one.")

    if args.auth_skey is None and check_env("auth_skey"):
        parser.error("--", args.auth_ikey.replace("_", "-"),"was not provided and isn't in environment variables. Please specify at least one.")

    elif args.resume_from_file is not None:
        if path.isfile(args.resume_from_file):
            output_file = args.resume_from_file
        else:
            parser.error("Couldn't find", args.resume_from_file)

    if args.ignore_list is not None:
        if not path.exists(args.ignore_list):
            parser.error(str(args.ignore_list), "not found.")

    if args.user_list is not None:
        if not path.exists(args.user_list):
            parser.error(str(args.args.user_list), "not found.")

    return args