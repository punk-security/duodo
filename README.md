Duo push campaign - Duo push notification spammer for testing MFA Auth fatigue

What this is for:
This script can be used to create a customisable "push" campaign for the Duo MFA app. You can customise:
- Who'll receieve push notifications. You can either send it to all users assocaited with a Duo account, or customise it - 1 or more Duo groups, a specific lsit of users (from user-list.txt), and include a list of users to ignore.
- The number of people who recieve the notification at once (batch size)
- The number of times to send push notifications to each user
- The time to wait between each push a user receives
- The time to wait between sending each "batch" of push notifications
- Resume the campaign from the last output file created
- Resume the campaign from a specific output file
- Customise the text that appears on the push notification

How to use:
1. If not passing the keys and hostname as an argument, you'll need to set the environemnt variables `admin_ikey`, `admin_skey` and `host` to the appropriate values. e.g. 
In Windows PowerShell:
    $ENV:ADMIN_IKEY="DIO..."
    $ENV:ADMIN_SKEY="..."
    $ENV:DUO_HOST="api-....duosecurity.com"
    $ENV:AUTH_IKEY="DIO..."
    $ENV:AUTH_SKEY="DIO..."

How to get the Duo API keys:
- Log in as an Admin user
- On the sidebar on the left, go to `Applications`
- Under Applications, select `Protect an application`
- Scroll down until you find `Admin API`, then click the protect button on the right.
- This'll take you to the endpoint's page. Scroll down to `Permissions` and tick `Grant read resource`
- At the top there'll be the Integration key, Secret key and API Hostname

Duo side:
This needs both the API's integration key and secret key to use, as well as Duo's API endpoint.
