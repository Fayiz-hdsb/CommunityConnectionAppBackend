#Steps to Operate
1. Create a Firebase project on [firebase](https://console.firebase.google.com/). You can use any project name
2. After creating the project, in authentication tab of Firebase panel (found under 'Build' in the side navigation bar), click get started, select 'Email/password' under 'Native Provider,' and enable Email/Password. 
3. Then, under 'users' click add user and add desired emailId and password. This will be the admin user who can approve listings. Copy the UID of this admin
4. Create a web project by clicking on "Project Overview," and then add web app icon. Register the app, but don't paste any code yet. Click continue to console
5. Click on settings icon next to "Project Overview," go to "Project settings" and then copy the Web API Key
6. Go to Service Accounts tab, select python option, and then click Generate new private key. Don't check-in this file in git. Add the file contents of this file under config/key.json
7. Add a .env file in config folder
   1. Add the copied web api key there using
        `API_KEY='YOUR_API_KEY'`
    This key can be obtained from firebase project setting tab->web api field
   2. Add the copied UID of admin using
        `ADMIN_UID='YOUR_ADMIN_UID'`
8. Under 'Build' in navigation panel, select Cloud Firestore, and create a database
9. Finally make sure .env and key.json are in your gitignore to prevent these credentials from getting checked into git
NOTE: IF YOU ENCOUNTER AN ERROR, YOU MIGHT NEED TO WAIT A FEW MINS BEFORE THE APP CAN RUN, THE API ENABLING CAN TAKE SOME TIME

**Run using the command in your shell/terminal:**

`flask --app main run --debug --port=8000`