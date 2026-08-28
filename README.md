# EqualLink

A Flask + MongoDB volunteer-matching platform, built from the Figma design:
login/signup, volunteer opportunity browsing + filtering + smart "Match"
scoring, volunteer profile / applications / favorites, and an organisation
side for posting opportunities and reviewing applicants.

## 1. Requirements

- Python 3.10+
- A running MongoDB instance (local `mongod`, or a free MongoDB Atlas cluster)

## 2. Setup

```bash
cd equallink
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` (or just export the variables) and point it at
your MongoDB:

```
SECRET_KEY=change-me
MONGO_URI=mongodb://localhost:27017
MONGO_DBNAME=equallink
```

## 3. Run

```bash
python app.py
```

Visit **http://127.0.0.1:5000** — you'll land on the login page. Click
"Sign up now" to create either a **Volunteer** or **Organisation** account.

## 4. How the pieces map to the design

| Page | Route |
|---|---|
| Login | `/login` |
| Sign up | `/signup` |
| Volunteer home (Opportunities + Filter + Match) | `/volunteer/home` |
| Volunteer Profile / Application / My Favorite | `/volunteer/workspace` (`#profile`, `#application`, `#favorite`) |
| Organisation home (all opportunities + Our Opportunities) | `/organisation/home` |
| Organisation Create / Profile / Applications | `/organisation/workspace` (`#create`, `#profile`, `#applications`) |

- Clicking the **EqualLink** logo always returns to the role's home page.
- The circular avatar top-right opens the dropdown (Profile / Application /
  My Favorite / Log out for volunteers; Profile / Create opportunities /
  Applications / Log out for organisations).
- The **Match** button scores every active opportunity against the
  volunteer's saved profile (category, location, available time, skills,
  opportunity offer — see `matching.py`) and shows the ranked results in a
  popup, each with a "View details" and "Save" action.
- Clicking "…" next to any row opens the opportunity/applicant detail popup.
- A volunteer must fill in their profile (Name, DOB, Contact, Location)
  before Matching or Applying is allowed.
- Only fields the user actually typed (name, dates, free text, etc.) render
  in the plain body font; every other label/button/heading uses the
  decorative display font, per the design.

## 5. Data model (MongoDB collections)

- `users` — login credentials + role (`volunteer` / `organisation`)
- `volunteer_profiles`, `organisation_profiles` — one doc per user
- `opportunities` — posted by organisations
- `applications` — a volunteer applying to an opportunity (`Pending` /
  `Accepted` / `Rejected`)
- `favorites` — a volunteer's saved opportunities

## 6. Notes

- Passwords are hashed with Werkzeug's `generate_password_hash`.
- All success/error toasts (e.g. "Save/ Update successfully!", "Submission
  failed. Please try again.") come from the flash-message / JSON-response
  strings in `app.py`, matching the design's message list.
- This build uses server-rendered Jinja templates + a small amount of
  vanilla JS (`static/js/main.js`) for dropdowns, modals and AJAX actions —
  no separate frontend build step required.
