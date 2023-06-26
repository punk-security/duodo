```
      ____              __   _____                      _ __       
     / __ \__  ______  / /__/ ___/___  _______  _______(_) /___  __
    / /_/ / / / / __ \/ //_/\__ \/ _ \/ ___/ / / / ___/ / __/ / / /
   / ____/ /_/ / / / / ,<  ___/ /  __/ /__/ /_/ / /  / / /_/ /_/ / 
  /_/    \__,_/_/ /_/_/|_|/____/\___/\___/\__,_/_/  /_/\__/\__, /  
                                         PRESENTS         /____/  
                          Duodo ✨
```

# Duodo
This tool is designed to test user MFA fatigue when continuously receiving unsolicited push notifications for Duo MFA. You can test how many of your users will accept unsolicited push notifications.

Duodo allows you to create customisable MFA push campaigns, allowing you to use to target only specific users and numbers, or Duo groups. You can also use an ignore list by itself, or in conjunction with these other options.

## Intro
This tool can be used to create a customisable "push" campaign for the Duo MFA app. You can customise:
- Who'll receive push notifications. You can either send it to all users associated with a Duo account, or customise it - 1 or more Duo groups, a specific list of users (from user-list.txt), and include a list of users to ignore.
- The number of people who receive the notification at once (batch size)
- The number of times to send push notifications to each user
- The time to wait between each push a user receives
- The time to wait between sending each "batch" of push notifications
- Resume the campaign from the last output file created
- Resume the campaign from a specific output file
- Customise the text that appears on the push notification

There are also 2 other options:
- List all groups you can use when doing the push campaigns. This requires both the admin ikey and skey be passed in, or set in the environment variables.
- Empty out the results folder that's created by default. This will ask you if you are sure you want to delete the folder. Any answer other the 'y' (without the quote marks) will not execute the command


NOTE: If not passing the API keys as an argument, you'll need to set the environment variables `admin_ikey`, `admin_skey`, `auth_ikey`, `auth_skey` to the appropriate values. e.g. 

```
Windows Powershell:
    $ENV:ADMIN_IKEY="..."
    $ENV:ADMIN_SKEY="..."
    $ENV:AUTH_IKEY="..."
    $ENV:AUTH_SKEY="..."
    
Windows CMD:
    set VAR_NAME="..."
    ...

Linux CLI:
    export VAR_NAME="..."
    ...
```

## How to get API keys:
- Log in as an Admin user
- On the sidebar on the left, go to `Applications`
- Under Applications, select `Protect an application`
- Scroll down until you find `Admin API`, then click the protect button on the right.
- This'll take you to the endpoint's page. Scroll down to `Permissions` and tick `Grant read resource`
- At the top there'll be the Integration key, Secret key and API Hostname

## Running Duodo:
You can run Duodo in docker by either passing the API keys in  each time, or setting them as environment variables.

Normal:
```
docker run punksecurity/duodo "host" [api keys] [commands]
```

Passing environment variables:
```
docker run punksecurity/duodo "host" [commands] -e ADMIN_IKEY="" ADMIN_SKEY="" AUTH_IKEY="" AUTH_SKEY=""
```
Passing in the API keys as environment variables allows you to rerun the container again without having to pass them in.


### Getting your results
To get your results out of Docker, run:
```
docker cp 'container':/app/results.csv /host/path/target
```

### Resume Campaign
If you need to resume a Duo push campaign, you can run:
```
docker run -v /results/on/host:/app/results [image name] [options] --resume-from-last
```
or
```
docker run -v /results/on/host:/app/results [image name] [options] --resume-from-file "/app/results/[resultsfile].csv"
```
`You will need to pass either the API keys or environment variables again.`

## Running Duodo locally:
Duodo can also be run locally, and has been tested with Python 3.11.

You'll need to install the dependencies in the requirements.txt by running the following command:
```
pip install -r requirements.txt
```

Then, Duodo can be run using:
```
py main.py "api-1234abcd.duosecurity.com" [options]
```

For example:
```
py main.py "api-1234abcd.duosecurity.com" --user-list "user-list.csv" --push-text "My test push"
```

## Get your results
You can get your results from the results folder in the root of the Duodo folder.
```
Duodo
|- results
    |- results12345.csv
```

### Resume a campaign
To resume a campaign running locally, you can run:
```
py main.py "host" --resume-from-last
```
or
```
py main.py "host" --resume-from-file "results/file.csv"
```

# Full Usage
```
usage: py main.py "api-1234abcd.duosecurity.com" [options]

Sends push notifications to all specified users, staggered over the specified period of time

positional arguments:
  host                  API host url. E.g. api-1234abcd.duosecurity.com

options:
  -h, --help            show this help message and exit
  -w USER_WAIT, --user-wait USER_WAIT
                        The amount of time in seconds to wait between each push notification sent to a specific user. This time does not include the time taken to wait for the notification to      
                        timeout or for the user to deny it. Defaults to 60 seconds if --user-pings is >1
  -u USER_PINGS, --user-pings USER_PINGS
                        The number of times to send a user a push notification in a row. Defaults to 1
  -b BATCH_SIZE, --batch-size BATCH_SIZE
                        The number of users to send push notifications to at once
  -t TIME_BETWEEN, --time-between TIME_BETWEEN
                        The amount of time in seconds to wait between each batch of push notifications
  --admin-ikey ADMIN_IKEY
                        Admin API integration key. Only required if ADMIN_IKEY environment variable not set.
  --admin-skey ADMIN_SKEY
                        Admin API secret key. Only required if ADMIN_SKEY environment variable not set.
  --auth-ikey AUTH_IKEY
                        Auth API integration key. Only required if AUTH_IKEY environment variable not set.
  --auth-skey AUTH_SKEY
                        Auth API secret key. Only required if AUTH_SKEY environment variable not set.
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        Full or relative path of the output file including name e.g. /results/results.csv. Defaults to results/result<datetime>.csv
  -f RESUME_FROM_FILE, --resume-from-file RESUME_FROM_FILE
                        Path of file containing results of a previous campaign to use to resume sending push notifications to and updating.
  -r, --resume-from-last
                        Resumes sending push notifications from the latest file produced in results folder at the root of this directory.
  -i IGNORE_LIST, --ignore-list IGNORE_LIST
                        Path to file of list of emails of users to ignore.
  -l USER_LIST, --user-list USER_LIST
                        Sends push notifications only to specified users in a provided file. Userlist format is either one of `email` or `email - phonenumber`. E.g. user-list.txt
  -p PUSH_TEXT, --push-text PUSH_TEXT
                        Text to display in push notification. Defaults to 'Login'.
  -g BY_GROUPS, --by-groups BY_GROUPS
                        Send push notifications to all users in specified groups. Groups are separated by a comma e.g. "group1, group2"
  --list-groups         To be used alone, no other commands will be executed. Lists groups associate with a given endpoint. Requires the admin integration key and secret key.
  --empty-results       To be used alone, no other commands will be executed. Deletes all files in the results folder.
```
