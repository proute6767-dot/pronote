import os, json, urllib.request, datetime as dt
import pronotepy

c = pronotepy.Client(os.environ["PRONOTE_URL"], username=os.environ["PRONOTE_USER"], password=os.environ["PRONOTE_PASS"])
seen = set(json.load(open("state.json"))) if os.path.exists("state.json") else set()
today = dt.date.today()
for l in c.lessons(today, today + dt.timedelta(days=7)):
    if not l.canceled:
        continue
    subject = l.subject.name if l.subject else "Cours"
    key = f"{l.start.isoformat()}-{subject}"
    if key in seen:
        continue
    msg = f"{subject} annulé : {l.start.strftime('%A %d/%m à %Hh%M')}"
    req = urllib.request.Request("https://ntfy.sh/" + os.environ["NTFY_TOPIC"], data=msg.encode("utf-8"), headers={"Title": "Cours annule", "Priority": "high"})
    urllib.request.urlopen(req)
    seen.add(key)
json.dump(sorted(seen), open("state.json", "w"))
