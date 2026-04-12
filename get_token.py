import json, os

creds_path = os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")
with open(creds_path) as f:
    creds = json.load(f)
print(creds["claudeAiOauth"]["accessToken"])
