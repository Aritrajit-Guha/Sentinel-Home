"""
Feature engineering helpers.

Placeholder for combining raw hazard-model output (damage_grade probability)
with household-profile features (occupant count, vulnerable members) into
the final personalized urgency score described in Phase 3 of the proposal.
"""

def household_risk_multiplier(household: dict) -> float:
    """
    Returns a multiplier (>=1.0) applied to the base structural risk score
    based on household vulnerability. Placeholder logic — replace with a
    calibrated formula, or a second small model trained on SVI-style
    indicators once you decide on your composite scoring approach.
    """
    multiplier = 1.0
    if household.get("has_elderly_or_disabled_member"):
        multiplier += 0.15
    if household.get("household_size", 1) > 5:
        multiplier += 0.05
    if household.get("floor_number", 0) >= 3:
        multiplier += 0.05
    return multiplier
