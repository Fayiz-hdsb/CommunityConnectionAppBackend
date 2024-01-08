#Steps to Operate
1. Add a .env file in config folder
   1. Add your API_KEY there using
        `API_KEY=YOUR_API_KEY`
    This key can be obtained from firebase project setting tab->web api field
2. Add key.json in config folder (file for firebase configuration for admin sdk)

**Run using the command in your shell/terminal:**

`flask --app main run --debug --port=8000`