import os, json, time, datetime as dt
from flask import Flask, request, abort, send_file, Response
import pronotepy

app = Flask(__name__)
_c = {}

def g(o, n, default=None):
    return getattr(o, n, default)

def safe(f):
    try:
        return f()
    except Exception:
        return []

def client():
    c = pronotepy.Client(os.environ["PRONOTE_URL"], username=os.environ["PRONOTE_USER"], password=os.environ["PRONOTE_PASS"])
    if not c.logged_in:
        raise RuntimeError("Connexion Pronote refusee")
    return c

def build():
    c = client()
    today = dt.date.today()
    p = c.current_period
    name = lambda x: x.subject.name if g(x, "subject") else "?"
    d = {}
    d["lessons"] = safe(lambda: sorted([{"s": name(l), "start": l.start, "end": l.end, "room": g(l, "classroom"), "canceled": bool(g(l, "canceled")), "status": g(l, "status"), "test": bool(g(l, "test"))} for l in c.lessons(today - dt.timedelta(days=3), today + dt.timedelta(days=21))], key=lambda x: x["start"]))
    d["grades"] = safe(lambda: [{"s": name(x), "grade": x.grade, "out_of": x.out_of, "coef": x.coefficient, "date": x.date, "avg": g(x, "average"), "min": g(x, "min"), "max": g(x, "max"), "comment": g(x, "comment")} for x in p.grades])
    d["averages"] = safe(lambda: [{"s": name(x), "me": x.student, "cls": g(x, "class_average")} for x in p.averages])
    d["overall"] = safe(lambda: p.overall_average)
    d["homework"] = safe(lambda: sorted([{"s": name(x), "text": x.description, "date": x.date, "done": x.done} for x in c.homework(today, today + dt.timedelta(days=21))], key=lambda x: str(x["date"])))
    d["absences"] = safe(lambda: [{"from": x.from_date, "ok": x.justified} for x in p.absences])
    d["delays"] = safe(lambda: [{"date": x.date, "min": x.minutes, "ok": x.justified} for x in p.delays])
    d["punishments"] = safe(lambda: [{"date": g(x, "given"), "what": g(x, "circumstances")} for x in p.punishments])
    d["infos"] = safe(lambda: [{"title": x.title, "by": g(x, "author"), "text": g(x, "content")} for x in c.information_and_surveys()])
    d["messages"] = safe(lambda: [{"title": g(x, "subject"), "by": g(x, "creator"), "unread": g(x, "unread")} for x in c.discussions()])
    d["menus"] = safe(lambda: [{"date": m.date, "meals": [[f.name for f in (g(m, k) or [])] for k in ("first_meal", "main_meal", "side_meal", "cheese", "dessert")]} for m in c.menus(today, today + dt.timedelta(days=7))])
    return d

def courses():
    c = client()
    today = dt.date.today()
    out = []
    for l in reversed(c.lessons(today - dt.timedelta(days=10), today)):
        try:
            ct = l.content
        except Exception:
            continue
        if ct and (g(ct, "title") or g(ct, "description")):
            out.append({"s": l.subject.name if l.subject else "?", "date": l.start, "title": g(ct, "title"), "text": g(ct, "description"), "test": bool(g(l, "test"))})
        if len(out) >= 25:
            break
    return out

def cached(key, fn, fresh):
    if fresh or time.time() - _c.get(key, (0, 0))[0] > 120:
        _c[key] = (time.time(), fn())
    return Response(json.dumps(_c[key][1], default=str), mimetype="application/json")

def auth():
    if request.headers.get("X-Code") != os.environ["APP_CODE"]:
        abort(401)

@app.route("/")
def home():
    return send_file("index.html")

@app.route("/api/data")
def data():
    auth()
    return cached("d", build, request.args.get("fresh"))

@app.route("/api/courses")
def api_courses():
    auth()
    return cached("c", courses, request.args.get("fresh"))
