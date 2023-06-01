from multiprocessing import Pool
from os import environ, path, listdir, makedirs
import time, datetime, argparse, sys, csv
import duo_client


parser = argparse.ArgumentParser(
    prog='Duo Push Notification Tester',
    description='Sends push notifications to all specified users, staggered over the specificed period of time',
)

parser.add_argument('-b', '--batch-size', type=int, help='The number of users to send push notifications to at once') # number of users to ping at once
parser.add_argument('-p', '--user-pings', type=int, help='The number of times to send a user a push notificaiton in a row. Defaults to 1') # number of users to ping at once
parser.add_argument('-w', '--user-wait', type=int, help='The amount of time in seconds to wait between each push notification sent to a specific user. This time does not include the time taken to wait for the notificaiton to timeout or for the user to deny it. Defaults to 60 seconds if --user-pings is >1') # number of users to ping at once
parser.add_argument('-t', '--time-between', type=int, help='The amount of time in seconds to wait between each batch of push notifications') # defaults to 5 minutes
parser.add_argument('--admin-ikey', help="Admin API integration key") # integration key
parser.add_argument('--admin-skey', help="Admin API secret key") # secret key
parser.add_argument('--auth-ikey', help="Auth API integration key") # integration key
parser.add_argument('--auth-skey', help="Auth API secret key") # secret key
parser.add_argument('-a', '--host', required=True, help="API hot url")
parser.add_argument('-o', '--output-file', help='Name of the output file')
parser.add_argument('-i', '--ignore-list', action='store_true', help='List of usernames to ignore') # from last file or specific file?
parser.add_argument('-l', '--resume-from-last', action='store_true', help="Resumes sending push notifications from the lastest file produced in results")
parser.add_argument('-r', '--resume-from-file', action='store_true', help='Resumes sending push notifications from output file provided') # , required="--output-file" in sys.argv
parser.add_argument('-u', '--user-list', action='store_true', help="Sends push notifications only to specificed users. Userlist format is `firstname lastname - phonenumber`")
parser.add_argument('-n', '--push-text', help="Text to display in push notification. Defaults to 'TEST PUSH'")
parser.add_argument('-g', '--by-group', help="Send push notifications to all users in a specific group")


parser.add_argument('--list-groups', help="To be used alone, no other commands will be executed. Lists groups associate with a given endpoint")

# TODO: can list groups - needs to be used alone / ignore all other commands

# Can manually set enviroemtn vriables
#environ["admin_ikey"] = ""
#environ["admin_skey"] = ""
#environ["auth_ikey"] = ""
#environ["auth_skey"] = ""
#host = ""

makedirs("results", exist_ok=True)

args = parser.parse_args()

if args.admin_ikey is not None:
    admin_ikey = args.admin_ikey
else:
    try:
        admin_ikey = environ['ADMIN_IKEY']
    except KeyError:
        print("--admin_ikey not provided and key not in environment variables. Please specify at least 1.")
        exit()

if args.admin_skey is not None:
    admin_skey = args.admin_skey
else:
    try:
        admin_skey = environ['admin_skey']
    except KeyError:
        print("--admin_skey not provided and key not in environment variables. Please specify at least 1.")
        exit()

if args.auth_ikey is not None:
    auth_ikey = args.auth_ikey
else:
    try:
        auth_ikey = environ['auth_ikey']
    except KeyError:
        print("--auth_ikey not provided and key not in environment variables. Please specify at least 1.")
        exit()

if args.auth_skey is not None:
    auth_skey = args.auth_skey
else:
    try:
        auth_skey = environ['auth_skey']
    except KeyError:
        print("--auth_skey not provided and key not in environment variables. Please specify at least 1.")
        exit()

if args.host is not None:
    host = args.host
else:
    print("A host url must be provided. e.g. api-1234abcd.duosecurity.com")
    exit()

admin_api = duo_client.Admin(ikey=admin_ikey, skey=admin_skey, host=host)
auth_api = duo_client.Auth(ikey=auth_ikey, skey=auth_skey, host=host)

# List groups
if args.list_groups is not None:
    groups = admin_api.get_groups()
    

# Batch Size
if args.batch_size is not None:
    batch_size = args.batch_size
else:
    batch_size = 3

# Time between
if args.time_between is not None:
    time_between = args.time_between
else:
    time_between = 300 # 5 minutes

# User pings
user_wait = 0
if args.user_pings is not None:
    user_pings = args.user_pings
    # Amount of time to wait between pings
    if args.user_wait is not None:
        user_wait = args.user_wait
    else:
        user_wait = 60
else:
    if args.user_wait is not None:
        print("--user-pings not speccified. Only use this command if you're sending more then 1 ping to a user.")
        exit()
    user_pings = 1

if args.output_file is not None:
    output_file = "results/" + args.output_file
else:
    output_file = "results/results" + datetime.datetime.strftime(datetime.datetime.now(), "%d%m%Y-%H%M%S") + ".csv"

if args.ignore_list:
    if not path.exists("ignore-list.txt"):
        print("ignore-list.txt not found.")
        exit()

if args.user_list:
    if not path.exists("user-list.txt"):
        print("user-list.txt not found.")
        exit()

if args.resume_from_file and args.resume_from_last:
    print("Only one of resume-from-file or resume-from-last may be be specified")
    exit()

if args.resume_from_last:
    print("Resuming from last modified results file")
    files = listdir(path.abspath('results'))
    last_modified_list = {}

    if len(files) == 0:
        print("No previous results files was found to use.")
        exit()

    for file in files:
        last_modified_list[str(path.getmtime("results/"+file))] = file

    int_keys = []
    for key in last_modified_list.keys():
        int_keys.append(float(key))

    int_keys.sort(reverse=True)

    output_file = "results/" + last_modified_list[str(int_keys[0])]


if args.resume_from_file:
    if args.output_file is not None:
    
        try:
            f = open("results/" + args.output_file, 'r')
            f.close()
        except FileNotFoundError:
            print("File 'results/" + args.output_file + "' not found.")
            exit()
    else:
        print("No output file specified.")
        exit()


if args.push_text is not None:
    push_text = args.push_text
else:
    push_text = "TEST PUSH"


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


# Reactivates user if they've been locked out
# This doesn't work. Keep getting lockedout emails
#def remove_user_lockout(user_id):
#    """
#    Reactivates users that have been locked out of their account.
#
#    :param user_id: string of user objects
#    :type user_id: str
#    """    
#    u = admin_api.update_user(user_id, status="active")
#    if u["status"] != "active":
#        return False
#    return True


def retrieve_users() -> list:
    """
    Gets all users associated with the Duo account from the endpoint.

    https://github.com/duosecurity/duo_client_python/blob/master/duo_client/admin.py
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
    users = []

    groups = admin_api.get_groups()
    g = ""
    for group in groups:
        if group == args.by_group:
            g = group

    if len(g) == 0:
        print("Group not found, list of avaiable groups:")
        for i in groups:
            print(i["name"])
        exit()

    try:
        group_users = admin_api.get_group_users(g["group_id"]) # TODO: fix
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
        with open("user-list.txt", "r") as file:
            spamreader = csv.reader(file, delimiter='-')
            for row in spamreader:
                print(row)
                users.append(row) # list of lists, in the format [['firstname lastname - phonenumber'], [...]]
    except FileNotFoundError:
        print("user-list.txt not found.")
        exit()


    filtered_users_details = []
    # Gets all user objects that have the same realname as those provided in user-list.txt, and removes phones with phone numbers that weren't specified in the list
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
            print(unable_to_push)
            print(i)

            result +=  [[i[2], i[0], "", "", "\'Unable to push notification\'", str(datetime.datetime.now()), "\n"]]
            print(result)

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
    Sends a push notification to a user's registered devices, and records the response (Whether the notification was accepted, denied or timedout)

    :param user_id: The user_id of the user
    :type user_id: str
    :param devices: A list of device_ids
    :type devices: list
    :return: list of output information (username, user_id, response_status, responses_message)
    :rtype: list
    """     
    lockout_reattempt = 0
    for i in range(0, user_pings):
        res = auth_api.auth("push", user_id=user_id, type=push_text, device=devices) # , async_txn=True
        
        if res["status"] == "fraud":
            break
        # Lockout will return status as deny or timeout sometimes instead of lockout even when locked out in admin panel
        if lockout_reattempt < 2 and (res["status"] == "locked_out" or "Your account is disabled" in res["status_msg"]):
            break

        print(res)
        if res["result"] == "allow":
            break
        if i != user_pings:
            print("user_wait", user_wait)
            time.sleep(user_wait)

    return [username, user_id, res['result'], res["status"],"\'" + res['status_msg'] + "\'", str(datetime.datetime.now())]



def get_ignore_list() -> list:
    """
    Gets a list of usernames to ignore from the ignore-list.txt

    :return: List of usernames to ignore when sending out push notifications
    :rtype: list
    """    
    skip_users = []
    with open("ignore-list.txt", "r") as file:
        spamreader = csv.reader(file, delimiter=',')
        for row in spamreader:
            skip_users.append(row[0])

    return skip_users



def filter_users(all_users:list, skip_users:list) -> list:
    """
    Removes users from the users list that have already recieved push notifications, and that are in the skip users list.

    :param all_users: List containing multiple User objects
    :type all_users: list
    :param skip_users: List of usernames
    :type skip_users: list
    :return: Filtered users list of objects
    :rtype: list
    """    
    users_to_remove = []

    # if output file specified - checks if user has already been used and skips them if they have
    if args.resume_from_file or args.resume_from_last:
        with open(output_file, 'r') as f:
            spamreader = csv.reader(f)
            for row in spamreader:
                users_to_remove.append(row[0])

    # Removes user's we don't want to send notifications to from all_users list
    for user in skip_users:
        users_to_remove.append(user)

    #users_to_remove = set(all_usernames).intersection(set(skip_users))

    # Removes inactive users and users in the ignore list
    i = 0
    while i < len(all_users):
        # If user is not active or username is in the list of users to remove
        if all_users[i]["status"] != "active" or all_users[i]["username"] in users_to_remove:
            del all_users[i]
        else:
            i += 1

    return all_users


def check_duo_push(users: list) -> dict:
    """
    Checks to see if user uses Duo Mobile for push notifications. If it's enabled , it's added to a list assocaited with the user_id

    :param users: A list of user IDs
    :type users: list
    :return: Returns a dictionary containing the user_id, username and device ids
    :rtype: dict
    """    
    users_details = {}
    for user in users:
        # Get user's associated phones and checks if push is activated on any of them
        phones = []

        ### DEBUG
        phones = admin_api.get_user_phones(user["user_id"])

        useable_phones = []
        for phone in phones:
            # Checks id push notifications enabled
            if phone["activated"] == True:
                for capability in phone["capabilities"]:
                    if capability == "push": 
                        useable_phones.append(phone["phone_id"])
                
        users_details[user["user_id"]] = {"username": user["username"], "devices": useable_phones}

    return users_details

if __name__ == '__main__':
    main()
