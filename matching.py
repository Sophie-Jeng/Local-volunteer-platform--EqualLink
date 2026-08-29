"""Matching engine: compares a volunteer profile against every opportunity
and returns a ranked list with a percentage match score.

Dimensions compared (each contributes equally, 20% weight):
  category | location | available time | skills | opportunity offer
"All" on either side of a dimension is treated as a wildcard (auto match).
"""
"""Matching function has been approved.
"""
def _has_overlap(wanted, offered):
    """True if the two lists share an item, or either side selected 'All'."""
    wanted = set(wanted or [])
    offered = set(offered or [])
    if "All" in wanted or "All" in offered:
        return True
    return len(wanted & offered) > 0


def _overlap_ratio(wanted, offered):
    """Fraction of `wanted` items that are satisfied by `offered` (0..1)."""
    wanted = set(wanted or [])
    offered = set(offered or [])
    if not wanted:
        return 1.0
    if "All" in wanted or "All" in offered:
        return 1.0
    if not offered:
        return 0.0
    return len(wanted & offered) / len(wanted)


def score_opportunity(profile, opp):
    """Return a 0-100 match score between a volunteer profile and one opportunity."""
    scores = []

    # category (multi on profile, single on opportunity)
    scores.append(1.0 if _has_overlap(profile.get("category", []), [opp.get("category", "")]) else 0.0)

    # location (single on both)
    p_loc = profile.get("location") or "All"
    o_loc = opp.get("location") or "All"
    scores.append(1.0 if (p_loc == "All" or o_loc == "All" or p_loc == o_loc) else 0.0)

    # available time (multi vs single time-slot)
    scores.append(1.0 if _has_overlap(profile.get("available_time", []), [opp.get("time_slot", "")]) else 0.0)

    # skills the volunteer can provide vs skills the opportunity is looking for
    scores.append(_overlap_ratio(opp.get("skills", []), profile.get("skills", [])))

    # opportunity offer the volunteer wants vs what the opportunity provides
    scores.append(_overlap_ratio(profile.get("opportunity_offer", []), opp.get("offer", [])))

    return round(sum(scores) / len(scores) * 100)


def find_matches(profile, all_opportunities, min_score=1):
    ranked = []
    for opp in all_opportunities:
        if opp.get("status") != "Active":
            continue
        pct = score_opportunity(profile, opp)
        if pct >= min_score:
            ranked.append((pct, opp))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked
