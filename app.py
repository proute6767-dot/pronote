import os, json, time, datetime as dt
from flask import Flask, request, abort, send_file, Response
import pronotepy

app = Flask(__name__)
_cache = {"t": 0, "d": None}

def g(o, n, default=None):
    return getattr(o, n, default)

def safe(f):
    try:
        return f()
    except Exception:
        return []

def build():
    c = pronotepy.Client(os.environ["PRONOTE_URL"], username=os.environ["PRONOTE_USER"], password=os.environ["PRONOTE_PASS"])
    if not c.logged_in:
        raise RuntimeError("Connexion Pronote refusee")
    today = dt.date.today()
    p = c.current_period
    name = lambda x: x.subject.name if g(x, "subject") else "?"
    d = {}
    d["lessons"] = safe(lambda: sorted([{"s": name(l), "start": l.start, "end": l.end, "room": g(l, "classroom"), "canceled": bool(g(l, "canceled")), "status": g(l, "status")} for l in c.lessons(today, today + dt.timedelta(days=7))], key=lambda x: x["start"]))
    d["grades"] = safe(lambda: [{"s": name(x), "grade": x.grade, "out_of": x.out_of, "coef": x.coefficient, "date": x.date, "avg": g(x, "average")} for x in p.grades])
    d["averages"] = safe(lambda: [{"s": name(x), "me": x.student, "cls": g(x, "class_average")} for x in p.averages])
    d["overall"] = safe(lambda: p.overall_average)
    d["homework"] = safe(lambda: [{"s": name(x), "text": x.description, "date": x.date, "done": x.done} for x in c.homework(today, today + dt.timedelta(days=14))])
    d["absences"] = safe(lambda: [{"from": x.from_date, "to": x.to_date, "ok": x.justified, "why": g(x, "reasons")} for x in p.absences])
    d["delays"] = safe(lambda: [{"date": x.date, "min": x.minutes, "ok": x.justified, "why": g(x, "reasons")} for x in p.delays])
    d["punishments"] = safe(lambda: [{"date": g(x, "given"), "why": g(x, "reasons"), "what": g(x, "circumstances")} for x in p.punishments])
    d["infos"] = safe(lambda: [{"title": x.title, "by": g(x, "author"), "date": g(x, "creation_date"), "text": g(x, "content")} for x in c.information_and_surveys()])
    d["messages"] = safe(lambda: [{"title": g(x, "subject"), "by": g(x, "creator"), "date": g(x, "date"), "unread": g(x, "unread")} for x in c.discussions()])
    d["menus"] = safe(lambda: [{"date": m.date, "meals": [[f.name for f in (g(m, k) or [])] for k in ("first_meal", "main_meal", "side_meal", "cheese", "dessert")]} for m in c.menus(today, today + dt.timedelta(days=5))])
    return d

@app.route("/")
def home():
    return send_file("index.html")

@app.route("/api/data")
def data():
    if request.headers.get("X-Code") != os.environ["APP_CODE"]:
        abort(401)
    if time.time() - _cache["t"] > 120 or request.args.get("fresh"):
        _cache["d"] = build()
        _cache["t"] = time.time()
    return Response(json.dumps(_cache["d"], default=str), mimetype="application/json")
