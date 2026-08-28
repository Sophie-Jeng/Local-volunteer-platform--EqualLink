from pymongo import MongoClient
from config import Config

_client = MongoClient(Config.MONGO_URI)
db = _client[Config.MONGO_DBNAME]

users = db.users                      # {_id, role, email, username/org_name, password_hash, created_at}
volunteer_profiles = db.volunteer_profiles   # keyed by user_id
organisation_profiles = db.organisation_profiles  # keyed by user_id
opportunities = db.opportunities
applications = db.applications
favorites = db.favorites

# ---- shared option vocabularies (used by <select> dropdowns everywhere) ----
CATEGORY_OPTIONS = ["All", "Human Rights", "Disability Services", "Animal Welfare", "Community Serves"]
LOCATION_OPTIONS = ["All", "Brisbane", "Sydney", "Melbourne", "Perth", "Adelaide",
                     "Canberra", "Hobart", "Darwin", "Gold Coast"]
TIME_OPTIONS = ["All", "Morning", "Afternoon", "Evening", "All day",
                "Short-term", "Long-term", "Weekend"]
SKILL_OPTIONS = ["All", "Administration", "Accounting", "Physical Support", "Mentor Support",
                  "Communication", "Teamwork & Collaboration", "Time Management & Punctuality",
                  "Problem-Solving & Adaptability", "Customer Service & Hospitality"]
OFFER_OPTIONS = ["All", "Short-term Session", "Certificate of Service",
                  "Letters of Recommendation", "Orientation & Training", "Network & Connect"]


def init_indexes():
    users.create_index("email", unique=True)
    opportunities.create_index("org_id")
    applications.create_index([("volunteer_id", 1), ("opportunity_id", 1)], unique=True)
    favorites.create_index([("volunteer_id", 1), ("opportunity_id", 1)], unique=True)
