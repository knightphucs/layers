"""
LAYERS - Admin helpers 
=====================================
Tiny pure functions shared by the auth backend and the views. Kept in their
own module (no heavy imports) so they're trivially unit-testable and so
importing them never drags in the DB engine.
"""

from typing import List


def is_admin_role(role) -> bool:
    """Mirror of require_admin in anti_cheat.py: accepts string OR enum role.
    Single source of truth for "is this user an admin?" in the panel."""
    return "ADMIN" in str(role).upper()


def parse_pks(raw: str) -> List[str]:
    """SQLAdmin passes selected primary keys as a comma-separated string in
    ?pks=... — turn it into a clean list, dropping blanks."""
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]
