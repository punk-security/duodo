from multiprocessing import Pool
from os import environ, path, listdir, makedirs
import time, datetime, argparse, sys, csv
import duo_client


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
duo_keys.add_argument('host', required=True, help="API host url. E.g. api-1234abcd.duosecurity.com")
duo_keys.add_argument('--admin-ikey', help="Admin API integration key") # integration key
duo_keys.add_argument('--admin-skey', help="Admin API secret key") # secret key
duo_keys.add_argument('--auth-ikey', help="Auth API integration key") # integration key
duo_keys.add_argument('--auth-skey', help="Auth API secret key") # secret key

output_exclusive = parser.add_mutually_exclusive_group(required=False)
output_exclusive.add_argument('-o', '--output-file', default=None, help='Full or relative path of the output file including name e.g. /results/results.csv. Defaults to results/result<datetime>.csv')
output_exclusive.add_argument('-f', '--resume-from-file', help="Path of file containing results of a previous campaign to use to resume sending push notifications to and updating")
output_exclusive.add_argument('-l', '--resume-from-last', action='store_true', default=False, help="Resumes sending push notifications from the latest file produced in results")

parser.add_argument('-i', '--ignore-list', help='Path to file of list of usernames to ignore')
parser.add_argument('-u', '--user-list', action='store_true', default=False, help="Sends push notifications only to specified users. Userlist format is `firstname lastname - phonenumber`")
parser.add_argument('-p', '--push-text', default="Login", help="Text to display in push notification. Defaults to 'Login'")
parser.add_argument('-g', '--by-group', help="Send push notifications to all users in a specific group")

parser.add_argument('--list-groups', help="To be used alone, no other commands will be executed. Lists groups associate with a given endpoint")

# Can manually set environment variables
#environ["admin_ikey"] = ""
#environ["admin_skey"] = ""
#environ["auth_ikey"] = ""
#environ["auth_skey"] = ""

makedirs("results", exist_ok=True)

def get_env(key:str) -> str:
    """
    Attempts to get environment 

    :param key: _description_
    :type key: str
    :return: _description_
    :rtype: str
    """    
    try:
        var = environ[key.upper()]
    except KeyError:
        print("--", key.replace("_", "-"),"was not provided and isn't not in environment variables. Please specify at least one.")
        exit()
    return var

args = parser.parse_args()

if args.admin_ikey is not None:
    admin_ikey = args.admin_ikey
else:
    admin_ikey = get_env("admin_ikey")

if args.admin_skey is not None:
    admin_skey = args.admin_skey
else:
    admin_skey = get_env("admin_skey")

if args.auth_ikey is not None:
    auth_ikey = args.auth_ikey
else:
    auth_ikey = get_env("auth_ikey")

if args.auth_skey is not None:
    auth_skey = args.auth_skey
else:
    auth_skey = get_env("auth_skey")

host = args.host


admin_api = duo_client.Admin(ikey=admin_ikey, skey=admin_skey, host=host)
auth_api = duo_client.Auth(ikey=auth_ikey, skey=auth_skey, host=host)


# List groups
if args.list_groups is not None:
    groups = admin_api.get_groups()
    for group in groups:
        print("-", group["name"])
    exit()


batch_size = args.batch_size
time_between = args.time_between
user_pings = args.user_pings
user_wait = args.user_wait

if args.output_file is not None:
    output_file = args.output_file
else:
    output_file = "results/results" + datetime.datetime.strftime(datetime.datetime.now(), "%Y%m%d-%H%M%S") + ".csv"

# Mutually exclusive resume from last and file, so only 1 can be passed in
if args.resume_from_last is not None:
    output_file = args.resume_from_last

if args.resume_from_file is not None:
    output_file = args.resume_from_file


if args.ignore_list is not None:
    if not path.exists(args.ignore_list):
        print(str(args.ignore_list), "not found.")
        exit()

if args.user_list is not None:
    if not path.exists(args.user_list):
        print(str(args.args.user_list), "not found.")
        exit()


def main():
    skip_users = []
    print("Getting all Duo users from Duo")
    all_users = retrieve_users()

    if args.ignore_list:
        print("Getting ignore-list users")
        skip_users = get_ignore_list()

    if args.user_list:
        print("Filtering out Duo users to only get those specified in user-list.txt")
        all_users = get_users_from_list(all_users)

    if args.by_group:
        print("Getting all users by group")
        all_users = filter_by_group(all_users)

    print("Filtering Duo users")
    users = filter_users(all_users, skip_users)

    print("Checking for users with push notifications enabled")
    pushable_users = check_duo_push(users)

    print("Pushing notifications...")
    send_push_notifications(pushable_users)

    print("Finished")


def retrieve_users() -> list:
    """
    Gets all users associated with the Duo account from the endpoint.

    :return: A complete list of users
    :rtype: list
    """    
    offset = 0
    users = admin_api.get_users(limit=300)

    while True:
        offset += 300
        try:
            res = admin_api.get_users(offset=offset, limit=offset)
            if res == []:
                break
            users += res
        except RuntimeError: 
            break

    return users


def filter_by_group(all_users:list) -> list:
    """
    Filters out users from a give list of user objects using 

    :param all_users: _description_
    :type all_users: list
    :return: _description_
    :rtype: list
    """    
    users = []

    groups = admin_api.get_groups()
    g = ""
    for group in groups:
        if group == args.by_group:
            g = group

    if len(g) == 0:
        print("Group not found, list of available groups:")
        for i in groups:
            print(i["name"])
        exit()

    try:
        group_users = admin_api.get_group_users(g["group_id"])
    except Exception as e:
        print("Unable to get group", g["name"])
        print(e)
        exit()

    users = []

    for gu in group_users:
        for user in all_users:
            if gu["user_id"] == user["user_id"]:
                users.append(user)

    return users


def get_users_from_list(all_users:list) -> list:
    """
    Gets real user's names and phone numbers from user-list.txt, and filters `all_users` dictionary to return only users with the names provided in the list, and only with phone object with the given number.

    :param all_users: A dictionary containing user objects
    :type all_users: dict
    :return: A list of filtered user objects, containing only the relevant users
    :rtype: list
    """    
    users = []
    # Gets all users from user-list.txt
    try:
        with open(args.user_list, "r") as file:
            spamreader = csv.reader(file, delimiter='-')
            for row in spamreader:
                print(row)
                users.append(row)
    except FileNotFoundError:
        print(args.user_list, "not found.")
        exit()


    filtered_users_details = []
    # Gets all user objects that have the same realname as those provided in user list, and removes phones with phone numbers that weren't specified in the list
    for user in all_users:
        for needed_user in users:
            # See if this user object is the user we need
            if user["realname"].lower() in needed_user[0].strip().lower():
                # Removes phones that won't be used.
                for i in range(0, len(user["phones"])):
                    # Removes the first 3 characters of the number as this is a country code e.g. (+44)77..., 
                    # and first character of the regular number e.g. (0)77...
                    if user["phones"][i]["number"][3:] == needed_user[1][1:].replace(" ", ""):
                        user["phones"] = [user["phones"][i]]
                        break
                
                filtered_users_details.append(user)

    return filtered_users_details

    

def send_push_notifications(users_list:list):
    """
    Sends a Duo push notification to one of the users' phones.

    :param users_list: A dictionary containing the users_id, username and devices or each user
    :type users_list: dict
    """    
    keys = list(users_list.keys())

    while len(keys) != 0:
        print("Sending push notifications...")
        users_to_push = []
        unable_to_push = []

        for i in range(0, batch_size):
            try:
                k = keys.pop()
                if len(users_list[k]["devices"]) == 0:
                    unable_to_push.append([k, users_list[k]["devices"], users_list[k]["username"]])
                else:
                    users_to_push.append((k, users_list[k]["devices"], users_list[k]["username"]))
            except IndexError:
                break

        result = []

        print("users:", users_to_push)
        if len(users_to_push) > 0:
            try:
                with Pool(batch_size) as p:
                    r = p.starmap(send_notification_query, users_to_push)
                    result += r
            except KeyboardInterrupt:
                exit()
            pass

        for i in unable_to_push:
            # i[2] is the user's username and i[0] is the user's user_id
            result +=  [[i[2], i[0], "", "", "\'Unable to push notification\'", str(datetime.datetime.now()), "\n"]]

        with open(output_file, "a", newline='\n') as file:
            spamwriter = csv.writer(file, delimiter=',')
            for res in result:
                spamwriter.writerow(res)

        if len(keys) != 0:
            print("waiting")
            time.sleep(time_between) 
            print("going")

    return


def send_notification_query(user_id:str, devices:list, username:str) -> list:
    """
    Sends a push notification to a user's registered devices, and records the response (Whether the notification was accepted, denied or timed out)

    :param user_id: The user_id of the user
    :type user_id: str
    :param devices: A list of device_ids
    :type devices: list
    :return: list of output information (username, user_id, response_status, responses_message)
    :rtype: list
    """     

    for i in range(0, user_pings):
        res = auth_api.auth("push", user_id=user_id, type=args.push_text, device=devices)
        
        if res["status"] == "fraud":
            break

        # Lockout will return status as deny or timeout sometimes instead of lockout even when locked out in admin panel
        if res["status"] == "locked_out" or "Your account is disabled" in res["status_msg"]:
            break

        if res["result"] == "allow":
            break

        if i != user_pings:
            time.sleep(user_wait)

    return [username, user_id, res['result'], res["status"],"\'" + res['status_msg'] + "\'", str(datetime.datetime.now())]


def get_ignore_list() -> list:
    """
    Gets a list of usernames to ignore from the ignore-list.txt

    :return: List of usernames to ignore when sending out push notifications
    :rtype: list
    """    
    skip_users = []
    with open(args.ignore_list, "r") as file:
        spamreader = csv.reader(file, delimiter=',')
        for row in spamreader:
            skip_users.append(row[0])

    return skip_users


def filter_users(all_users:list, skip_users:list) -> list:
    """
    Removes users from the users list that have already received push notifications, and that are in the skip users list.

    :param all_users: List containing multiple User objects
    :type all_users: list
    :param skip_users: List of usernames
    :type skip_users: list
    :return: Filtered users list of objects
    :rtype: list
    """    
    users_to_remove = []

    # if output file specified - checks if user has already been used and skips them if they have
    with open(output_file, 'r') as f:
        spamreader = csv.reader(f)
        for row in spamreader:
            users_to_remove.append(row[0])

    # Removes user's we don't want to send notifications to from all_users list
    for user in skip_users:
        users_to_remove.append(user)

    # Creates a list with the inactive users and ignore list users removed
    filtered_users = [user for user in all_users if user["status"] == "active" or user["username"] not in users_to_remove]

    return filtered_users


def check_duo_push(users: list) -> dict:
    """
    Checks to see if user uses Duo Mobile for push notifications. If it's enabled , it's added to a list associated with the user_id

    :param users: A list of user IDs
    :type users: list
    :return: Returns a dictionary containing the user_id, username and device ids
    :rtype: dict
    """    
    users_details = {}
    for user in users:
        # Get user's associated phones and checks if push is activated on any of them
        try:
            phones = admin_api.get_user_phones(user["user_id"])
        except Exception as e:
            print("A problem occurred when trying to get", user["name"], "phone numbers")
            users_details[user["user_id"]] = {"username": user["username"], "devices": []}
            continue

        useable_phones = [phone["phone_id"] for phone in phones if phone["activated"] and "push" in phone["capabilities"]]
        users_details[user["user_id"]] = {"username": user["username"], "devices": useable_phones}

    return users_details

if __name__ == '__main__':
    main()
