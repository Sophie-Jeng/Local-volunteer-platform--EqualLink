from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
load_dotenv()

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from db import (users, volunteer_profiles, organisation_profiles, opportunities,
                 applications, favorites, init_indexes,
                 CATEGORY_OPTIONS, LOCATION_OPTIONS, TIME_OPTIONS, SKILL_OPTIONS, OFFER_OPTIONS)
from matching import find_matches

app = Flask(__name__)
app.config.from_object(Config)

OPTION_LISTS = dict(categories=CATEGORY_OPTIONS, locations=LOCATION_OPTIONS,
                     times=TIME_OPTIONS, skills=SKILL_OPTIONS, offers=OFFER_OPTIONS)


@app.context_processor
def inject_globals():
    def page_url(page):
        args = request.args.to_dict(flat=False)
        args["page"] = [str(page)]
        pairs = []
        for k, vlist in args.items():
            for v in vlist:
                pairs.append(f"{k}={v}")
        return "&".join(pairs)
    return dict(options=OPTION_LISTS, current_user=get_current_user(), page_url=page_url)


# ---------------------------------------------------------------- helpers --
def oid(id_str):
    try:
        return ObjectId(id_str)
    except (InvalidId, TypeError):
        return None


def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    u = users.find_one({"_id": oid(uid)})
    return u


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if not get_current_user():
            flash("You don't have an account.", "error")
            return redirect(url_for("login"))
        return view(*a, **kw)
    return wrapped


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*a, **kw):
            u = get_current_user()
            if not u or u.get("role") != role:
                flash("Something went wrong. Please try again.", "error")
                return redirect(url_for("index"))
            return view(*a, **kw)
        return wrapped
    return decorator


def get_volunteer_profile(user_id):
    return volunteer_profiles.find_one({"user_id": user_id}) or {}


def get_org_profile(user_id):
    return organisation_profiles.find_one({"user_id": user_id}) or {}


def multi(field):
    """Read a repeated form field (checkbox group) as a list, honouring 'All'."""
    vals = request.form.getlist(field)
    return vals


def paginate(cursor_list, page, per_page):
    start = (page - 1) * per_page
    total = len(cursor_list)
    items = cursor_list[start:start + per_page]
    has_prev = page > 1
    has_next = start + per_page < total
    return items, has_prev, has_next


# --------------------------------------------------------------- home/nav --
@app.route("/")
def index():
    u = get_current_user()
    if not u:
        return public_home()
    if u["role"] == "volunteer":
        return redirect(url_for("volunteer_home"))
    return redirect(url_for("organisation_home"))


def public_home():
    """Homepage for a visitor who is not logged in: can browse opportunities
    but cannot reach a profile page or apply/save/match."""
    page = max(int(request.args.get("page", 1)), 1)
    all_opps = list(opportunities.find({"status": "Active"}).sort("_id", -1))
    items, has_prev, has_next = paginate(all_opps, page, app.config["PER_PAGE"])
    return render_template("public_home.html", opportunities=items,
                            page=page, has_prev=has_prev, has_next=has_next)


# ------------------------------------------------------------------ auth --
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        u = users.find_one({"email": email})
        if not u or not check_password_hash(u["password_hash"], password):
            flash("You don't have an account.", "error")
            return redirect(url_for("login"))
        session["user_id"] = str(u["_id"])
        flash("Log in successfully!", "success")
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        role = request.form.get("role", "volunteer")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        username = request.form.get("username", "").strip()

        if "@" not in email or "." not in email.split("@")[-1]:
            flash("Please enter a valid email address.", "error")
            return redirect(url_for("signup"))
        if users.find_one({"email": email}):
            flash("This email is already registered. Log in instead, or use 'Forgot your password?' to reset it.", "error")
            return redirect(url_for("signup"))

        user_doc = {
            "role": role,
            "email": email,
            "username": username,
            "password_hash": generate_password_hash(password),
            "created_at": datetime.utcnow(),
        }
        result = users.insert_one(user_doc)
        uid = str(result.inserted_id)

        if role == "volunteer":
            volunteer_profiles.insert_one({"user_id": uid, "name": username})
        else:
            organisation_profiles.insert_one({"user_id": uid, "org_name": username})

        session["user_id"] = uid
        flash("Sign up successfully!", "success")
        return redirect(url_for("index"))
    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------------------------- volunteer --
@app.route("/volunteer/home")
@login_required
@role_required("volunteer")
def volunteer_home():
    u = get_current_user()
    categories = [c for c in request.args.getlist("category") if c and c != "All"]
    times = [t for t in request.args.getlist("time") if t and t != "All"]
    skills = [s for s in request.args.getlist("skill") if s and s != "All"]
    offers = [o for o in request.args.getlist("offer") if o and o != "All"]
    location = request.args.get("location", "")

    q = {"status": "Active"}
    if categories:
        q["category"] = {"$in": categories}
    if location and location != "All":
        q["location"] = location
    if times:
        q["time_slot"] = {"$in": times}
    if skills:
        q["skills"] = {"$in": skills}
    if offers:
        q["offer"] = {"$in": offers}

    page = max(int(request.args.get("page", 1)), 1)
    all_opps = list(opportunities.find(q).sort("_id", -1))
    items, has_prev, has_next = paginate(all_opps, page, app.config["PER_PAGE"])

    fav_ids = {f["opportunity_id"] for f in favorites.find({"volunteer_id": str(u["_id"])})}

    return render_template("volunteer/home.html", opportunities=items,
                            page=page, has_prev=has_prev, has_next=has_next,
                            fav_ids=fav_ids, filters=request.args)


@app.route("/volunteer/workspace")
@login_required
@role_required("volunteer")
def volunteer_workspace():
    u = get_current_user()
    uid = str(u["_id"])
    profile = get_volunteer_profile(uid)

    apage = max(int(request.args.get("apage", 1)), 1)
    my_apps = list(applications.find({"volunteer_id": uid}).sort("_id", -1))
    app_items, a_has_prev, a_has_next = paginate(my_apps, apage, app.config["PER_PAGE"])
    for a in app_items:
        opp = opportunities.find_one({"_id": oid(a["opportunity_id"])}) or {}
        a["_opp"] = opp

    fpage = max(int(request.args.get("fpage", 1)), 1)
    my_favs = list(favorites.find({"volunteer_id": uid}).sort("_id", -1))
    fav_items, f_has_prev, f_has_next = paginate(my_favs, fpage, app.config["PER_PAGE"])
    for f in fav_items:
        opp = opportunities.find_one({"_id": oid(f["opportunity_id"])}) or {}
        f["_opp"] = opp

    return render_template("volunteer/workspace.html", profile=profile, user=u,
                            app_items=app_items, a_has_prev=a_has_prev, a_has_next=a_has_next, apage=apage,
                            fav_items=fav_items, f_has_prev=f_has_prev, f_has_next=f_has_next, fpage=fpage)


@app.route("/volunteer/profile/save", methods=["POST"])
@login_required
@role_required("volunteer")
def volunteer_profile_save():
    u = get_current_user()
    uid = str(u["_id"])
    doc = {
        "user_id": uid,
        "name": request.form.get("name", "").strip(),
        "dob": request.form.get("dob", "").strip(),
        "contact_number": request.form.get("contact_number", "").strip(),
        "experience": request.form.get("experience", "").strip(),
        "more_info": request.form.get("more_info", "").strip(),
        "category": multi("category"),
        "location": request.form.get("location", "").strip(),
        "available_time": multi("available_time"),
        "skills": multi("skills"),
        "opportunity_offer": multi("opportunity_offer"),
    }

    required_text_fields = ["name", "dob", "contact_number", "experience", "more_info", "location"]
    required_list_fields = ["category", "available_time", "skills", "opportunity_offer"]
    missing = (not all(doc[f] for f in required_text_fields)
               or not all(doc[f] for f in required_list_fields))
    if missing:
        session["profile_draft"] = doc
        flash("Please fill in every field before saving.", "error")
        return redirect(url_for("volunteer_workspace") + "#profile")
 
    volunteer_profiles.update_one({"user_id": uid}, {"$set": doc}, upsert=True)
    flash("Save/ Update successfully!", "success")
    return redirect(url_for("volunteer_workspace") + "#profile")


@app.route("/volunteer/profile/delete", methods=["POST"])
@login_required
@role_required("volunteer")
def volunteer_profile_delete():
    u = get_current_user()
    uid = str(u["_id"])
    volunteer_profiles.delete_one({"user_id": uid})
    flash("Delete/ Close successfully!", "success")
    return redirect(url_for("volunteer_workspace") + "#profile")


def profile_is_complete(profile):
    required = ["name", "dob", "contact_number", "location"]
    return profile and all(profile.get(f) for f in required)


@app.route("/volunteer/apply/<opp_id>", methods=["POST"])
@login_required
@role_required("volunteer")
def volunteer_apply(opp_id):
    u = get_current_user()
    uid = str(u["_id"])
    profile = get_volunteer_profile(uid)
    if not profile_is_complete(profile):
        return jsonify(ok=False, message="Please complete your profile before applying."), 400
    opp = opportunities.find_one({"_id": oid(opp_id)})
    if not opp:
        return jsonify(ok=False, message="Something went wrong. Please try again."), 404
    if applications.find_one({"volunteer_id": uid, "opportunity_id": opp_id}):
        return jsonify(ok=False, message="You've already applied to this opportunity."), 400
    try:
        applications.insert_one({
            "volunteer_id": uid, "opportunity_id": opp_id, "org_id": opp["org_id"],
            "status": "Pending", "applied_at": datetime.utcnow(),
        })
    except Exception:
        return jsonify(ok=False, message="You've already applied to this opportunity."), 400
    return jsonify(ok=True, message="Applied successfully!")


@app.route("/volunteer/favorite/<opp_id>", methods=["POST"])
@login_required
@role_required("volunteer")
def volunteer_favorite(opp_id):
    u = get_current_user()
    uid = str(u["_id"])
    existing = favorites.find_one({"volunteer_id": uid, "opportunity_id": opp_id})
    if existing:
        favorites.delete_one({"_id": existing["_id"]})
        return jsonify(ok=True, saved=False, message="Removed from favorites.")
    opp = opportunities.find_one({"_id": oid(opp_id)})
    favorites.insert_one({"volunteer_id": uid, "opportunity_id": opp_id,
                           "org_name": opp.get("org_name") if opp else "",
                           "event_name": opp.get("event_name") if opp else ""})
    return jsonify(ok=True, saved=True, message="Save/ Update successfully!")


@app.route("/api/match", methods=["POST"])
@login_required
@role_required("volunteer")
def api_match():
    u = get_current_user()
    profile = get_volunteer_profile(str(u["_id"]))
    if not profile_is_complete(profile):
        return jsonify(ok=False, message="Please complete your profile before matching."), 400
    all_opps = list(opportunities.find({"status": "Active"}))
    ranked = find_matches(profile, all_opps)
    page = int(request.form.get("page", 1))
    per_page = 2
    start = (page - 1) * per_page
    page_items = ranked[start:start + per_page]
    based_on = ", ".join(filter(None, [
        ", ".join(profile.get("available_time", [])[:1]),
        ", ".join(profile.get("category", [])[:1]),
        profile.get("location", ""),
    ])) or "your profile"
    html = render_template("partials/match_results.html", ranked=page_items, page=page,
                            has_prev=page > 1, has_next=start + per_page < len(ranked),
                            based_on=based_on, total=len(ranked))
    return jsonify(ok=True, html=html)


# ---------------------------------------------------------------- shared --
@app.route("/fragments/opportunity/<opp_id>")
def fragment_opportunity(opp_id):
    """Public: a visitor can view opportunity details, but the template only
    offers Apply/Save actions once current_user is set (i.e. logged in)."""
    opp = opportunities.find_one({"_id": oid(opp_id)})
    if not opp:
        return "<p>Something went wrong. Please try again.</p>"
    u = get_current_user()
    is_owner = bool(u) and u["role"] == "organisation" and opp.get("org_id") == str(u["_id"])
    saved = False
    if u and u["role"] == "volunteer":
        saved = bool(favorites.find_one({"volunteer_id": str(u["_id"]), "opportunity_id": opp_id}))
    return render_template("partials/opportunity_detail.html", opp=opp, is_owner=is_owner, saved=saved)


@app.route("/fragments/application/<app_id>")
@login_required
@role_required("organisation")
def fragment_application(app_id):
    a = applications.find_one({"_id": oid(app_id)})
    if not a:
        return "<p>No applications found.</p>"
    profile = get_volunteer_profile(a["volunteer_id"])
    opp = opportunities.find_one({"_id": oid(a["opportunity_id"])}) or {}
    return render_template("partials/applicant_detail.html", application=a, profile=profile, opp=opp)


# ---------------------------------------------------------------- org --
@app.route("/organisation/home")
@login_required
@role_required("organisation")
def organisation_home():
    u = get_current_user()
    uid = str(u["_id"])

    page = max(int(request.args.get("page", 1)), 1)
    all_opps = list(opportunities.find({"status": "Active"}).sort("_id", -1))
    items, has_prev, has_next = paginate(all_opps, page, app.config["PER_PAGE"])

    opage = max(int(request.args.get("opage", 1)), 1)
    own = list(opportunities.find({"org_id": uid}).sort("_id", -1))
    own_items, o_has_prev, o_has_next = paginate(own, opage, app.config["PER_PAGE"])

    return render_template("organisation/home.html", opportunities=items,
                            page=page, has_prev=has_prev, has_next=has_next,
                            own_opportunities=own_items, opage=opage,
                            o_has_prev=o_has_prev, o_has_next=o_has_next)


@app.route("/organisation/workspace")
@login_required
@role_required("organisation")
def organisation_workspace():
    u = get_current_user()
    uid = str(u["_id"])
    profile = get_org_profile(uid)

    edit_id = request.args.get("edit")
    edit_opp = opportunities.find_one({"_id": oid(edit_id)}) if edit_id else None

    apage = max(int(request.args.get("apage", 1)), 1)
    apps = list(applications.find({"org_id": uid}).sort("_id", -1))
    app_items, a_has_prev, a_has_next = paginate(apps, apage, app.config["PER_PAGE"])
    for a in app_items:
        a["_opp"] = opportunities.find_one({"_id": oid(a["opportunity_id"])}) or {}
        vp = get_volunteer_profile(a["volunteer_id"])
        a["_volunteer_name"] = vp.get("name", "Volunteer")

    return render_template("organisation/workspace.html", profile=profile, user=u, edit_opp=edit_opp,
                            app_items=app_items, a_has_prev=a_has_prev, a_has_next=a_has_next, apage=apage)


@app.route("/organisation/profile/save", methods=["POST"])
@login_required
@role_required("organisation")
def organisation_profile_save():
    u = get_current_user()
    uid = str(u["_id"])
    doc = {
        "user_id": uid,
        "org_name": request.form.get("org_name", "").strip(),
        "contact_number": request.form.get("contact_number", "").strip(),
        "contact_email": request.form.get("contact_email", "").strip(),
        "more_info": request.form.get("more_info", "").strip(),
    }

    required_fields = ["org_name", "contact_number", "contact_email", "more_info"]
    if not all(doc[f] for f in required_fields):
        session["org_profile_draft"] = doc
        flash("Please fill in every field before saving.", "error")
        return redirect(url_for("organisation_workspace") + "#profile")
 
    organisation_profiles.update_one({"user_id": uid}, {"$set": doc}, upsert=True)
    flash("Save/ Update successfully!", "success")
    return redirect(url_for("organisation_workspace") + "#profile")


@app.route("/organisation/profile/delete", methods=["POST"])
@login_required
@role_required("organisation")
def organisation_profile_delete():
    u = get_current_user()
    organisation_profiles.delete_one({"user_id": str(u["_id"])})
    flash("Delete/ Close successfully!", "success")
    return redirect(url_for("organisation_workspace") + "#profile")


@app.route("/organisation/opportunity/save", methods=["POST"])
@login_required
@role_required("organisation")
def organisation_opportunity_save():
    u = get_current_user()
    uid = str(u["_id"])
    org_profile = get_org_profile(uid)
    time_slot = request.form.get("time_slot", "").strip()
    doc = {
        "org_id": uid,
        "org_name": org_profile.get("org_name") or u.get("username"),
        "event_name": request.form.get("event_name", "").strip(),
        "contact_number": request.form.get("contact_number", "").strip(),
        "contact_email": request.form.get("contact_email", "").strip(),
        "more_info": request.form.get("more_info", "").strip(),
        "category": request.form.get("category", "").strip(),
        "location": request.form.get("location", "").strip(),
        "time_slot": time_slot,
        "time_display": request.form.get("time_display", "").strip() or time_slot,
        "skills": multi("skills"),
        "offer": multi("offer"),
    }
    opp_id = request.form.get("opp_id")

    required_text_fields = ["event_name", "contact_number", "contact_email", "more_info",
                             "category", "location", "time_slot"]
    required_list_fields = ["skills", "offer"]
    missing = (not all(doc[f] for f in required_text_fields)
               or not all(doc[f] for f in required_list_fields))
    if missing:
        session["opportunity_draft"] = doc
        flash("Please fill in every field before saving.", "error")
        anchor = f"?edit={opp_id}#create" if opp_id else "#create"
        return redirect(url_for("organisation_workspace") + anchor)
 
    if opp_id:
        opportunities.update_one({"_id": oid(opp_id), "org_id": uid}, {"$set": doc})
    else:
        doc["status"] = "Active"
        doc["created_at"] = datetime.utcnow()
        opportunities.insert_one(doc)
    flash("Save/ Update successfully!", "success")
    return redirect(url_for("organisation_workspace") + "#create")


@app.route("/organisation/opportunity/<opp_id>/close", methods=["POST"])
@login_required
@role_required("organisation")
def organisation_opportunity_close(opp_id):
    u = get_current_user()
    opp = opportunities.find_one({"_id": oid(opp_id), "org_id": str(u["_id"])})
    if not opp:
        return jsonify(ok=False, message="Something went wrong. Please try again."), 404
    new_status = "Close" if opp.get("status") == "Active" else "Active"
    opportunities.update_one({"_id": opp["_id"]}, {"$set": {"status": new_status}})
    return jsonify(ok=True, status=new_status, message="Delete/ Close successfully!")


@app.route("/organisation/opportunity/<opp_id>/delete", methods=["POST"])
@login_required
@role_required("organisation")
def organisation_opportunity_delete(opp_id):
    u = get_current_user()
    opportunities.delete_one({"_id": oid(opp_id), "org_id": str(u["_id"])})
    flash("Delete/ Close successfully!", "success")
    return redirect(url_for("organisation_home"))


@app.route("/organisation/application/<app_id>/<decision>", methods=["POST"])
@login_required
@role_required("organisation")
def organisation_application_decide(app_id, decision):
    if decision not in ("Accepted", "Rejected"):
        return jsonify(ok=False, message="Something went wrong. Please try again."), 400
    u = get_current_user()
    a = applications.find_one({"_id": oid(app_id), "org_id": str(u["_id"])})
    if not a:
        return jsonify(ok=False, message="Something went wrong. Please try again."), 404
    applications.update_one({"_id": a["_id"]}, {"$set": {"status": decision}})
    return jsonify(ok=True, status=decision, message="Save/ Update successfully!")


# ------ Error handlers ----- #
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")

@app.errorhandler(500)
def internal_error(e):
    return render_template("500.html")

    
if __name__ == "__main__":
    try:
        init_indexes()
    except Exception as exc:  # pragma: no cover
        print("Mongo index setup skipped:", exc)
    app.run(debug=True, port=5000)
