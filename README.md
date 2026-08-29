# EqualLink
 
EqualLink is a volunteer-matching website. Volunteers can browse
opportunities, build a profile, apply, and get matched with organisations
based on category, location, time, skills and what the opportunity offers.
Organisations can post opportunities and review applicants.
 
Built with **Python (Flask)**, **MongoDB**, and **Bootstrap 5** for the UI.
 
## Who can do what
 
- **Visitor (not logged in):** browse opportunities, but can't view a
  profile page or apply.
- **Volunteer:** log in/out, create/edit/delete their profile, apply to
  opportunities, check application status, save favorites, and use the
  "Match" button to get ranked opportunity suggestions.
- **Organisation:** log in/out, manage their profile, post/edit/close/
  delete opportunities, and accept/reject applicants.
## Getting started
 
1. Install the requirements:
```bash
   pip install -r requirements.txt
```
2. Set up your MongoDB connection (edit `config.py` or set environment
   variables `SECRET_KEY`, `MONGO_URI`, `MONGO_DBNAME`).
3. Run the app:
```bash
   python app.py
```
4. Open **http://127.0.0.1:5000** in your browser.
## Project structure
 
```
app.py          # routes / main app logic
db.py           # MongoDB connection + collections + dropdown option lists
matching.py     # rule-based matching logic for the "Match" button
config.py       # settings (secret key, database connection, etc.)
templates/      # HTML pages (Jinja2)
static/         # CSS and JS
```
 
## Pages
 
| Page | Route |
|---|---|
| Visitor homepage | `/` |
| Login | `/login` |
| Sign up | `/signup` |
| Volunteer home | `/volunteer/home` |
| Volunteer profile / applications / favorites | `/volunteer/workspace` |
| Organisation home | `/organisation/home` |
| Organisation profile / create opportunity / applications | `/organisation/workspace` |
| Page not found | `404.html` |
| Server error | `500.html` |
 
## Form validation
 
Required fields must all be filled in before saving (profile forms, the
create-opportunity form, etc.). If something's missing, the page shows an
error message and nothing is saved — whatever you'd already typed stays
in the form so you don't have to retype it.
 
## Notes
 
- Passwords are hashed before being stored (never saved as plain text).
- A volunteer can't apply to the same opportunity twice.
- Matching is rule-based (not AI) — it compares the volunteer's profile
  against each opportunity across five fields, where each field can also
  be set to "All" as a wildcard.
