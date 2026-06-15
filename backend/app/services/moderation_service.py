"""
LAYERS - Content Moderation Service
==================================================
Masterplan pipeline:

    User Post → Text Filter → Safe?  → save (ACTIVE)
                            → Risky? → save but hold (PENDING, invisible to public)
                            → Unsafe?→ REJECT + warn user + reputation penalty

Three-tier decision instead of binary, because false positives on a
social app kill trust. Mild profanity gets held for review (FLAG),
only severe content (threats, sexual content about minors, doxxing
patterns) is hard-rejected.

DETECTION LAYERS
1. Severe list  → REJECT  (threats, CSAM-adjacent, sexual violence)
2. Profanity    → FLAG    (VN + EN starter lists, extend in banned_words.txt)
3. Contact/spam → FLAG    (phone numbers, URLs, emails — LAYERS is
                           anonymous-first; contact info is the #1 grooming
                           and spam vector)
4. Evasion handling: lowercase + leetspeak map (0→o, 1→i, 3→e…) +
   Vietnamese diacritic folding ("dit me" matches "địt mẹ")

IMAGE SCANNING
`scan_image()` is a pluggable stub returning SAFE. The interface is final;
swap the body for NudeNet / AWS Rekognition in a background worker later
(see SETUP.md → "Image scanning roadmap"). PHOTO artifacts therefore start
as FLAG → PENDING until an admin (or the future AI worker) approves —
safest default for launch.

USAGE (inside ArtifactService.create_artifact — see SETUP.md):

    initial_status = await ModerationService.enforce(
        db, user=user, context=ModerationContext.ARTIFACT_CREATE,
        content_type=data.content_type, payload=data.payload,
    )
    artifact = Artifact(..., status=initial_status)

IMPORTANT TRANSACTION NOTE
On REJECT we must persist the penalty + log even though the request fails
with 400. `enforce()` therefore COMMITS the penalty itself before raising
ModerationRejected. On ALLOW/FLAG it only flushes the log and participates
in the caller's transaction (same flush-not-commit pattern as XPService).
"""

import logging
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.moderation_log import ModerationLog

logger = logging.getLogger(__name__)


# ============================================================
# DECISIONS & RESULT
# ============================================================

class ModerationDecision(str, Enum):
    ALLOW = "ALLOW"    # publish immediately (status ACTIVE)
    FLAG = "FLAG"      # save but hold for review (status PENDING)
    REJECT = "REJECT"  # do not save; warn + reputation penalty


class ModerationContext(str, Enum):
    ARTIFACT_CREATE = "artifact_create"
    REPLY = "reply"
    NOTEBOOK_PAGE = "notebook_page"
    ADMIN_REVIEW = "admin_review"


class ModerationRejected(ValueError):
    """Raised on REJECT. Subclasses ValueError so the existing
    `except ValueError → 400` handlers in artifacts.py keep working."""


@dataclass
class ModerationResult:
    decision: ModerationDecision = ModerationDecision.ALLOW
    reasons: List[str] = field(default_factory=list)
    matched: List[str] = field(default_factory=list)  # which patterns hit

    def merge(self, other: "ModerationResult") -> "ModerationResult":
        """Combine results; the harshest decision wins."""
        order = [ModerationDecision.ALLOW, ModerationDecision.FLAG,
                 ModerationDecision.REJECT]
        if order.index(other.decision) > order.index(self.decision):
            self.decision = other.decision
        self.reasons = list(dict.fromkeys(self.reasons + other.reasons))
        self.matched = list(dict.fromkeys(self.matched + other.matched))
        return self


# ============================================================
# WORD LISTS — starter set. Extend via app/data/banned_words.txt
# (one word per line; lines starting with "!" go to the SEVERE list)
# ============================================================

# REJECT outright. Keep this list narrow and unambiguous.
SEVERE_WORDS = [
    # threats of violence (vi)
    "giết mày", "tao giết", "đâm chết mày", "chém chết",
    # threats (en)
    "kill you", "i will kill",
    # sexual content about minors (vi/en) — zero tolerance
    "ấu dâm", "child porn", "cp trade",
]

# FLAG → PENDING. Common profanity, vi + en.
PROFANITY_WORDS = [
    # vietnamese
    "địt", "địt mẹ", "đụ", "lồn", "cặc", "buồi", "đĩ",
    "đm", "dm", "vcl", "vkl", "clm", "cmm", "đcm", "cc", "cl", "vl",
    "óc chó", "súc vật", "con chó này",
    # english
    "fuck", "shit", "bitch", "cunt", "asshole", "whore", "slut",
    "fck", "fuk", "fock",  # common spellings after leet-normalization
]

# Short/ambiguous tokens: only match as a WHOLE word ("cc" flags,
# "soccer" does not). Everything not listed here matches as substring.
WHOLE_WORD_ONLY = {
    "đm", "dm", "vcl", "vkl", "clm", "cmm", "đcm", "cc", "cl", "vl",
    "đĩ", "đụ", "shit", "fck", "fuk", "fock",
}

# Contact-info / spam patterns → FLAG
PHONE_RE = re.compile(r"(?:\+?84|0)(?:[\s.\-]?\d){8,10}")
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
REPEAT_SPAM_RE = re.compile(r"(.)\1{9,}")  # same char 10+ times

# Leetspeak / symbol substitutions seen in evasion attempts
_LEET_MAP = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
    "7": "t", "@": "a", "$": "s", "!": "i",
})


def _fold(text: str) -> str:
    """Strip Vietnamese diacritics: 'địt mẹ' → 'dit me'."""
    text = text.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalize(text: str) -> str:
    """lowercase + de-leet + collapse 3+ repeated letters ('fuuuuck'→'fuck')."""
    text = text.lower().translate(_LEET_MAP)
    return re.sub(r"([a-zà-ỹ])\1{2,}", r"\1", text)


def _compile_patterns(entries: List[tuple]) -> List[re.Pattern]:
    """entries: (word, whole_word_only). Spaces in phrases match any
    whitespace run; whole-word entries get Vietnamese-aware boundaries."""
    patterns = []
    for word, whole_word in entries:
        escaped = re.escape(word.lower()).replace(r"\ ", r"\s+")
        if whole_word:
            escaped = rf"(?<![\wà-ỹ]){escaped}(?![\wà-ỹ])"
        patterns.append(re.compile(escaped))
    return patterns


def _load_extra_words() -> tuple:
    """Optional extension file: backend/app/data/banned_words.txt"""
    extra_severe, extra_profanity = [], []
    path = Path(__file__).resolve().parent.parent / "data" / "banned_words.txt"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("!"):
                extra_severe.append(line[1:].strip())
            else:
                extra_profanity.append(line)
        logger.info("Loaded %d extra banned words", len(extra_severe) + len(extra_profanity))
    return extra_severe, extra_profanity


_extra_severe, _extra_profanity = _load_extra_words()

# Pre-compile patterns. Diacritic-folded variants are generated ONLY for
# multi-word phrases ("địt mẹ" → "dit me", "óc chó" → "oc cho"). Folding
# single VN words collides with innocent text far too often — "cặc"→"cac"
# would match "các", "đĩ"→"di" would match "đi", "buồi"→"buoi" would match
# "buổi". Single-word diacritic evasion is left to the report system and
# the banned_words.txt extension file (documented tradeoff, see SETUP.md).
def _build_entries(words: List[str]) -> List[tuple]:
    entries = []
    for w in words:
        entries.append((w, w.lower() in WHOLE_WORD_ONLY))
        folded = _fold(w)
        if folded != w and " " in folded:
            entries.append((folded, True))  # folded phrases: always bounded
    return entries


SEVERE_PATTERNS = _compile_patterns(_build_entries(SEVERE_WORDS + _extra_severe))
PROFANITY_PATTERNS = _compile_patterns(_build_entries(PROFANITY_WORDS + _extra_profanity))

# Reputation penalties (User.modify_reputation clamps to 0..1000)
PENALTY_REJECT = -20        # auto-reject on creation
PENALTY_ADMIN_REMOVE = -30  # admin confirms content was bad


# ============================================================
# PURE TEXT FILTER (no DB — fully unit-testable)
# ============================================================

def check_text(text: Optional[str]) -> ModerationResult:
    """Run all text rules. Pure function — no DB, no side effects."""
    result = ModerationResult()
    if not text or not text.strip():
        return result

    norm = _normalize(text)
    folded = _fold(norm)

    for pattern in SEVERE_PATTERNS:
        m = pattern.search(norm) or pattern.search(folded)
        if m:
            result.decision = ModerationDecision.REJECT
            result.reasons.append("severe_content")
            result.matched.append(m.group(0))
            return result  # severe short-circuits everything

    for pattern in PROFANITY_PATTERNS:
        m = pattern.search(norm) or pattern.search(folded)
        if m:
            result.decision = ModerationDecision.FLAG
            result.reasons.append("profanity")
            result.matched.append(m.group(0))
            break  # one profanity reason is enough

    if PHONE_RE.search(text):
        result.merge(ModerationResult(ModerationDecision.FLAG, ["contact_info_phone"]))
    if URL_RE.search(text):
        result.merge(ModerationResult(ModerationDecision.FLAG, ["contact_info_url"]))
    if EMAIL_RE.search(text):
        result.merge(ModerationResult(ModerationDecision.FLAG, ["contact_info_email"]))
    if REPEAT_SPAM_RE.search(text):
        result.merge(ModerationResult(ModerationDecision.FLAG, ["repeat_spam"]))

    return result


# Which payload fields carry user text, per content type.
# Mirrors ArtifactService._validate_payload — keep the two in sync.
TEXT_FIELDS = {
    "LETTER": ["text"],
    "PAPER_PLANE": ["text"],
    "TIME_CAPSULE": ["text"],
    "PHOTO": ["caption"],
    "VOICE": ["transcript"],
    "VOUCHER": ["description"],
    "NOTEBOOK": [],  # pages are moderated one-by-one on append
}


def check_payload(content_type, payload: dict) -> ModerationResult:
    """Moderate every text field of an artifact payload.
    PHOTO/VOICE media additionally goes through scan_image (stub)."""
    ct = getattr(content_type, "value", str(content_type))
    result = ModerationResult()

    for field_name in TEXT_FIELDS.get(ct, []):
        value = (payload or {}).get(field_name)
        if isinstance(value, str):
            result.merge(check_text(value))

    if ct == "NOTEBOOK":
        for page in (payload or {}).get("pages", []):
            if isinstance(page, str):
                result.merge(check_text(page))

    # Media → image scan stub. Until real AI scanning is wired,
    # photos are held for review instead of trusted blindly.
    if ct == "PHOTO" and (payload or {}).get("url"):
        result.merge(scan_image((payload or {}).get("url")))

    return result


def scan_image(url: str) -> ModerationResult:
    """PLUGGABLE IMAGE SCAN — replace body with NudeNet / Rekognition later.

    Launch default: every photo is FLAG → PENDING → human review.
    When the AI worker exists it will approve/reject PENDING photos
    asynchronously, and this function can return ALLOW for pre-scanned
    uploads. The call-site contract never changes.
    """
    return ModerationResult(ModerationDecision.FLAG, ["photo_pending_scan"])


# ============================================================
# SERVICE — DB-aware enforcement
# ============================================================

class ModerationService:

    @staticmethod
    async def enforce(
        db: AsyncSession,
        user,  # User — duck-typed to keep this module import-light
        context: ModerationContext,
        content_type=None,
        payload: Optional[dict] = None,
        text: Optional[str] = None,
        artifact_id: Optional[uuid.UUID] = None,
    ):
        """Run the pipeline and act on the decision.

        Returns the initial ArtifactStatus value to persist:
          ALLOW → "ACTIVE",  FLAG → "PENDING"
        Raises ModerationRejected on REJECT (after committing the
        penalty + log — the caller's 400 must not roll those back).
        """
        if text is not None:
            result = check_text(text)
            excerpt_src = text
        else:
            result = check_payload(content_type, payload or {})
            excerpt_src = _first_text(content_type, payload or {})

        if result.decision == ModerationDecision.ALLOW:
            return "ACTIVE"

        log = ModerationLog(
            user_id=getattr(user, "id", None),
            artifact_id=artifact_id,
            context=context.value,
            decision=result.decision.value,
            reasons={"reasons": result.reasons, "matched": result.matched},
            excerpt=(excerpt_src or "")[:200] or None,
        )
        db.add(log)

        if result.decision == ModerationDecision.FLAG:
            await db.flush()  # participate in caller's transaction
            logger.info("Moderation FLAG user=%s reasons=%s",
                        getattr(user, "id", None), result.reasons)
            return "PENDING"

        # REJECT — penalty + log must survive the 400
        if user is not None and hasattr(user, "modify_reputation"):
            user.modify_reputation(PENALTY_REJECT)
        await db.commit()
        logger.warning("Moderation REJECT user=%s reasons=%s",
                       getattr(user, "id", None), result.reasons)
        raise ModerationRejected(
            "Nội dung vi phạm tiêu chuẩn cộng đồng LAYERS và đã bị từ chối. "
            f"Điểm uy tín của bạn bị trừ {abs(PENALTY_REJECT)}. "
            f"(reasons: {', '.join(result.reasons)})"
        )

    @staticmethod
    async def log_admin_action(
        db: AsyncSession,
        admin_id: uuid.UUID,
        artifact_id: uuid.UUID,
        decision: str,  # "ADMIN_APPROVE" | "ADMIN_REMOVE"
        note: Optional[str] = None,
    ) -> None:
        db.add(ModerationLog(
            user_id=admin_id,
            artifact_id=artifact_id,
            context=ModerationContext.ADMIN_REVIEW.value,
            decision=decision,
            reasons={"note": note} if note else {},
        ))
        await db.flush()


def _first_text(content_type, payload: dict) -> Optional[str]:
    ct = getattr(content_type, "value", str(content_type))
    for field_name in TEXT_FIELDS.get(ct, []):
        v = (payload or {}).get(field_name)
        if isinstance(v, str) and v.strip():
            return v
    return None
