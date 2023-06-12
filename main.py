import argparsing

from multiprocessing import Pool
from os import environ, path, makedirs, path, listdir
import time, datetime, csv, random, re,logging
import duo_client


# Makes a results folder if one doesn't already exist
makedirs("results", exist_ok=True)

args = argparsing.parse_args()

def get_env(key:str) -> str:
    """
    Attempts to get environment variables.

    :param key: Environment variable to fetch
    :type key: str
    :return: Value of environment variable
    :rtype: str
    """ 
    try:   
        return environ[key.upper()]
    except Exception as e:
        logging.exception("Unable to find environment variable for %s. Error: %s".format(key.upper(), e))
        exit()


host = args.host

if args.admin_ikey is not None:
    admin_ikey = args.admin_ikey 
else:
    admin_ikey = get_env("admin_ikey")

if args.admin_skey is not None:
    admin_skey = args.admin_skey 
else:
    admin_skey = get_env("admin_skey")

try:
    admin_api = duo_client.Admin(ikey=admin_ikey, skey=admin_skey, host=host)
except Exception as e:
    logging.exception("Unable to connect to Admin endpoint. Error: %s".format(e))
    exit()

logging.info("Set Admin API")

# List groups
if args.list_groups:
    try:
        groups = admin_api.get_groups()
    except Exception as e:
        logging.error("Unable to get groups. Error: %s".format(e))
    print("List of groups:")
    for group in groups:
        print("-", group["name"])
    exit()

if args.auth_ikey is not None:
    auth_ikey = args.auth_ikey 
else:
    auth_ikey = get_env("auth_ikey")

if args.auth_skey is not None:
    auth_skey = args.auth_skey 
else:
    auth_skey = get_env("auth_skey")

try:
    auth_api = duo_client.Auth(ikey=auth_ikey, skey=auth_skey, host=host)
except Exception as e:
    logging.exception("Unable to connect to Auth endpoint. Error: %s".format(e))
    exit()
logging.info("Set Auth API")

batch_size = args.batch_size
time_between = args.time_between
user_pings = args.user_pings
user_wait = args.user_wait

if args.output_file is not None:
    output_file = args.output_file

# Mutually exclusive resume from last and file, so only 1 can be passed in
elif args.resume_from_last:
    p = "results"
    files = [f for f in listdir(p) if path.isfile(path.join(p, f))]

    if len(files) == 0:
        logging.error("No files in results folder to resume from.")
        exit()

    f = {}
    for file in files:
        f[str(path.getmtime(p))] = file

    output_file = "results/" +  f[ str(max(f.keys())) ]

elif args.resume_from_file is not None:
    if path.isfile(args.resume_from_file):
        output_file = args.resume_from_file
    else:
        logging.error("Couldn't find %s".format(args.resume_from_file))
        exit()

else:
    output_file = "results/results" + datetime.datetime.strftime(datetime.datetime.now(), "%Y%m%d-%H%M%S") + ".csv"

logging.info("Set output file to %s".format(output_file))


def main():
    skip_users = []
    logging.info("Getting all Duo users from Duo")
    users = retrieve_users()

    if args.user_list:
        logging.info("Filtering out Duo users to only get those specified in user list.")
        users = get_users_from_list(users)

    if len(users) == 0:
        logging.info("No users will receive push notifications with current parameters provided")
        exit()

    if args.by_groups:
        logging.info("Getting all users by group")
        users = filter_by_groups(users)

    if len(users) == 0:
        logging.info("No users will receive push notifications with current parameters provided")
        exit()

    if args.ignore_list:
        logging.info("Getting ignore-list users")
        skip_users = get_ignore_list()

    logging.info("Filtering Duo users")
    users = filter_users(users, skip_users)

    if len(users) == 0:
        logging.info("No users will receive push notifications with current parameters provided")
        exit()

    if not path.isfile(output_file):
        open(output_file, 'w').close()

    logging.info("Checking for users with push notifications enabled")
    users = check_duo_push(users)

    logging.info("Pushing notifications...")
    logging.info("Results will be saved to: %s".format(path.abspath(output_file)))
    send_push_notifications(users)

    logging.info("Finished")


def retrieve_users() -> list:
    """
    Gets all users associated with the Duo account from the endpoint.

    :return: A complete list of users
    :rtype: list
    """    
    offset = 0
    try:
        users = admin_api.get_users(limit=300)
    except Exception as e:
        logging.error("Unable to get users from admin endpoint. Error: %s".format(e))
        exit()
    logging.info("Getting all users")

    while True:
        offset += 300
        try:
            res = admin_api.get_users(offset=offset, limit=offset)
            if res == []:
                break
            users += res
        except Exception as e: 
            logging.error("Error when calling admin get_users(). Error: %s".format(e))
            break

    if len(users) == 0:
        logging.error("No users retrieved using parameters provided")
        exit()

    return users


def filter_by_groups(all_users:list) -> list:
    """
    Filters out users from a give list of user objects using groups provided.

    :param all_users: list of user objects
    :type all_users: list
    :return: list of user objects who are part of the groups provided 
    :rtype: list
    """    
    users = []

    # Split up user input
    g = [group.strip() for group in args.by_groups.split(",")]

    try:
        groups_list = admin_api.get_groups()
    except Exception as e:
        logging.error("Unable to get groups from endpoint. Error: %s".format(e))
        exit()

    logging.info("Getting all groups")

    groups_to_use = [group for group in groups_list if group["name"] in g]


    if len(groups_to_use) != len(g):
        print("Not all groups have been found.")
        print("Continue with the following groups only?")
        for i in groups_to_use:
            print(i)
        p = input("[y/N]")
        if p == "y":
            pass
        else:
            exit()
    
    users = []

    for user in all_users:
        for group in user["groups"]:
            if group["name"] in groups_to_use:
                users.append(user)
                break

    return users


def get_users_from_list(all_users:list) -> list:
    """
    Gets real user's email and optionally their phone numbers from user list, and filters `all_users` dictionary to return only users with the names provided in the list, and only with phone object with the given number.

    :param all_users: A dictionary containing user objects
    :type all_users: dict
    :return: A list of filtered user objects, containing only the relevant users
    :rtype: list
    """    
    # Gets all users from user list
    try:
        with open(args.user_list, "r") as file:
            spamreader = csv.reader(file, delimiter='-')
            filtered_users = { row[0].strip() : re.sub('[^\d]', '', row[1]) if len(row) > 1 else None for row in spamreader }
    except FileNotFoundError:
        logging.error("%s not found".format(args.user_list))
        exit()

    filtered_users_keys = list(filtered_users.keys())
    new_users = []

    for user in all_users:
        if user["email"] not in filtered_users_keys:
            continue
        
        if len(user["phones"]) == 0:
            logging.info("No phone numbers associated with %s. Skipping.".format( user["email"]))
            continue

        useable_phones = [phone["number"] for phone in user["phones"] if phone["activated"] and "push" in phone["capabilities"]]

        if len(useable_phones) == 0:
            logging.warning("No phones with push notifications activated for %s. Skipping.".format(user["email"]))
            continue

        phone_number = "+" + filtered_users[user["email"]].strip()

        if phone_number not in useable_phones:
            logging.warning("Unable to use provided phone - %s - number for %s. Skipping.".format(phone_number, user["email"]))
            continue

        if phone_number is None:
            user["phones"] = [random.choice(user["phones"])]
        else:
            p = [phone for phone in user["phones"] if phone["number"] == phone_number]
            if p != phone_number:
                logging.warning("Unable to find given phone number for %s. Selecting a random phone number instead.".format(user["email"]))
                p = random.choice(user["phones"])

            user["phones"] = [p]

        new_users.append(user)

    return new_users

    
def send_push_notifications(users_list:list):
    """
    Sends a Duo push notification to one of the users' phones.

    :param users_list: A dictionary containing the users_id, username and devices or each user
    :type users_list: dict
    """    
    keys = list(users_list.keys())

    while len(keys) != 0:
        logging.info("Sending push notifications")
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
        for i in unable_to_push:
            # i[2] is the user's username and i[0] is the user's user_id
            result +=  [[i[2], i[0], "", "", "\'Unable to push notification\'", str(datetime.datetime.now()), "\n"]]

        if len(users_to_push) > 0:
            try:
                with Pool(batch_size) as p:
                    r = p.starmap(send_notification_query, users_to_push)
                    result += r
            except KeyboardInterrupt:
                logging.info("Operation canceled, exiting.")
                exit()
            pass

        with open(output_file, "a", newline='\n') as file:
            spamwriter = csv.writer(file, delimiter=',')
            for res in result:
                spamwriter.writerow(res)

        if len(users_to_push) == 0:
            continue

        if len(keys) != 0:
            logging.info("Waiting %s seconds to send next batch...".format(time_between))
            time.sleep(time_between) 
 
    return


def send_notification_query(user_id:str, devices:list, username:str) -> list:
    """
    Sends a push notification to a user's registered devices, and records the response (Whether the notification was accepted, denied or timed out).

    :param user_id: The user_id of the user
    :type user_id: str
    :param devices: A list of device_ids
    :type devices: list
    :return: list of output information (username, user_id, response_status, responses_message)
    :rtype: list
    """     

    for i in range(0, user_pings):
        try:
            res = auth_api.auth("push", user_id=user_id, type=args.push_text, device=devices)
        except Exception as e:
            res = {'result': '', 'status': 'invalid_request', 'status_msg': 'Unable to ping user'}
            break
        
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
    Gets a list of user emails to ignore from the ignore list.

    :return: List of user's emails
    :rtype: list
    """    
    skip_users = []
    with open(args.ignore_list, "r") as file:
        spamreader = csv.reader(file, delimiter=',')
        for row in spamreader:
            try:
                skip_users.append(row[0])   
            except IndexError:
                continue
    logging.info("Got ignore list")
    return skip_users


def filter_users(all_users:list, skip_users:list) -> list:
    """
    Removes users from the users list that have already received push notifications, and that are in the skip users list.

    :param all_users: List containing multiple User objects
    :type all_users: list
    :param skip_users: List of user emails
    :type skip_users: list
    :return: Filtered users list of objects
    :rtype: list
    """    
    users_to_remove = []

    # if output file specified - checks if user has already been used and skips them if they have
    if args.resume_from_last or args.resume_from_file:
        with open(output_file, 'r') as f:
            spamreader = csv.reader(f)
            for row in spamreader:
                users_to_remove.append(row[0])

    # Creates a list with the inactive users and ignore list users removed
    filtered_users = [user for user in all_users if user["status"] == "active" and user["email"] not in skip_users and user["username"] not in users_to_remove]
    logging.info("Filtered users")
    return filtered_users


def check_duo_push(users: list) -> dict:
    """
    Checks to see if user uses Duo Mobile for push notifications. If it's enabled, it's added to a list associated with the user_id.

    :param users: A list of user IDs
    :type users: list
    :return: Returns a dictionary containing the user_id, username and device ids
    :rtype: dict
    """    
    users_details = {}

    for user in users:
        useable_phones = [phone["phone_id"] for phone in user["phones"] if phone["activated"] and "push" in phone["capabilities"]]

        if len(useable_phones) == 0:
            logging.warning("No useable phones for %s. User will not be added to push campaign.".format(user["email"]))
        else:
            users_details[user["user_id"]] = {"username": user["username"], "devices": useable_phones}
        
    return users_details


if __name__ == '__main__':
    main()
