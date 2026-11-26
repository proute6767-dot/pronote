import os, json, urllib.request, datetime as dt
import pronotepy

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
c = pronotepy.Client(os.environ["PRONOTE_URL"], username=os.environ["PRONOTE_USER"], password=os.environ["PRONOTE_PASS"])
seen = set(json.load(open("state.json"))) if os.path.exists("state.json") else set()
today = dt.date.today()
for l in c.lessons(today, today + dt.timedelta(days=14)):
    st = (getattr(l, "status", None) or "").strip()
    low = st.lower()
    if not (l.canceled or any(w in low for w in ("annul", "remplac", "absent", "modif", "chang", "dispens"))):
        continue
    label = st if st else "annulé"
    subject = l.subject.name if l.subject else "Cours"
    key = f"{l.start.isoformat()}-{subject}-{label}"
    if key in seen:
        continue
    msg = f"{subject} : {label} le {JOURS[l.start.weekday()]} {l.start.strftime('%d/%m à %Hh%M')}"
    req = urllib.request.Request("https://ntfy.sh/" + os.environ["NTFY_TOPIC"], data=msg.encode("utf-8"), headers={"Title": "Changement de cours", "Priority": "high"})
    urllib.request.urlopen(req)
    seen.add(key)
json.dump(sorted(seen), open("state.json", "w"))
