# API Reference (draft)

## POST /api/households
Register a household. See backend/app/models/household.py for schema.

## POST /api/alerts/{household_id}/confirm-safe
Household confirms safety, stands down escalation timer.

## GET /api/admin/status
System health / scheduler status.
