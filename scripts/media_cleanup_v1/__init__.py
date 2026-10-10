"""Media library quality audit and smart cleanup (V1).

Dry-run first. Never permanently deletes production media.
Status changes live in manifest metadata (quarantined / rejected / active).
"""

__version__ = "1.0.0"

QUALITY_TIERS = (
    "PREMIUM",
    "GOOD",
    "ACCEPTABLE",
    "LOW",
    "LEGACY",
    "UNCERTAIN",
)

ACTIVE_STATUSES = frozenset({"", "active", "approved", None})
HIDDEN_STATUSES = frozenset({"quarantined", "rejected"})
