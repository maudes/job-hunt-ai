import requests, json

board = "wemolo"
res = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{board}")
data = res.json()

print(f"Status: {res.status_code}")
print(f"Job count: {len(data.get('jobs', []))}")
for job in data.get("jobs", []):
    print(job.get("jobUrl"))