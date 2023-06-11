```
      ____              __   _____                      _ __       
     / __ \__  ______  / /__/ ___/___  _______  _______(_) /___  __
    / /_/ / / / / __ \/ //_/\__ \/ _ \/ ___/ / / / ___/ / __/ / / /
   / ____/ /_/ / / / / ,<  ___/ /  __/ /__/ /_/ / /  / / /_/ /_/ / 
  /_/    \__,_/_/ /_/_/|_|/____/\___/\___/\__,_/_/  /_/\__/\__, /  
                                         PRESENTS         /____/  
                          Duodo ✨
```

# Duo Push Campaign

Duo push notification spammer for testing MFA auth fatigue

### Intro
This script can be used to create a customisable "push" campaign for the Duo MFA app. You can customise:
- Who'll receive push notifications. You can either send it to all users associated with a Duo account, or customise it - 1 or more Duo groups, a specific list of users (from user-list.txt), and include a list of users to ignore.
- The number of people who receive the notification at once (batch size)
- The number of times to send push notifications to each user
- The time to wait between each push a user receives
- The time to wait between sending each "batch" of push notifications
- Resume the campaign from the last output file created
- Resume the campaign from a specific output file
- Customise the text that appears on the push notification

There are also 2 other options:
- List all groups you can use when doing the push campaigns based on users in specific groups
- Empty out the results folder that's created by default. This will ask you if you are sure you want to delete the folder. Any answer other the 'y' (without the quote marks) will not execute the command


NOTE: If not passing the API keys as an argument, you'll need to set the environment variables `admin_ikey`, `admin_skey`, `auth_ikey`, `auth_skey` to the appropriate values. e.g. 
In Windows PowerShell:
```
$ENV:ADMIN_IKEY="..."
$ENV:ADMIN_SKEY="..."
$ENV:AUTH_IKEY="..."
$ENV:AUTH_SKEY="..."
```


### Running Duodo:
```
python .\main.py "api-1234abcd.duosecurity.com" --user-list "user-list.csv" --push-text "My test login"
```

### Running Duodo in Docker:
```
Windows Powershell:
    $ENV:ADMIN_IKEY="..."
    $ENV:ADMIN_SKEY="..."
    $ENV:AUTH_IKEY="..."
    $ENV:AUTH_SKEY="..."
    
Windows CMD:
    set ADMIN_IKEY="..."
    set ADMIN_SKEY="..."
    set AUTH_IKEY="..."
    set AUTH_SKEY="..."

docker run punksecurity/duodo 'hostapi' [commands]
```

For example:
```
docker run punksecurity/duodo -e 'host' --admin-ikey '...' --admin-skey '...' --auth-ikey '...' --auth-skey '...' --output-file 'results/myOutput.csv' 
```

```
docker run punksecurity/duodo 'host' --push-text 'My login test' --resume-from-last --ignore-list 'ignore-list.csv' --user-list 'user-list.csv' 
```

### How to get API keys:
- Log in as an Admin user
- On the sidebar on the left, go to `Applications`
- Under Applications, select `Protect an application`
- Scroll down until you find `Admin API`, then click the protect button on the right.
- This'll take you to the endpoint's page. Scroll down to `Permissions` and tick `Grant read resource`
- At the top there'll be the Integration key, Secret key and API Hostname
