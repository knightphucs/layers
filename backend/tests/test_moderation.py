"""
LAYERS - Moderation tests
Pure-logic tests for the text filter — no DB required.
Run: pytest tests/test_moderation.py -v
"""

import pytest

from app.services.moderation_service import (
    ModerationDecision,
    ModerationResult,
    check_payload,
    check_text,
)


class TestCleanContent:
    def test_clean_vietnamese_allows(self):
        r = check_text("Hôm nay mình đã đi dạo quanh hồ Con Rùa, đẹp lắm!")
        assert r.decision == ModerationDecision.ALLOW
        assert r.reasons == []

    def test_clean_english_allows(self):
        r = check_text("Left a little memory here for whoever finds it next.")
        assert r.decision == ModerationDecision.ALLOW

    def test_empty_and_none_are_safe(self):
        assert check_text("").decision == ModerationDecision.ALLOW
        assert check_text(None).decision == ModerationDecision.ALLOW
        assert check_text("   ").decision == ModerationDecision.ALLOW


class TestProfanityFlag:
    def test_vietnamese_profanity_flags(self):
        r = check_text("thằng này óc chó thật")
        assert r.decision == ModerationDecision.FLAG
        assert "profanity" in r.reasons

    def test_english_profanity_flags(self):
        r = check_text("this place is fucking amazing")
        assert r.decision == ModerationDecision.FLAG

    def test_diacritic_evasion_caught(self):
        # "dit me" (no diacritics) must still match "địt mẹ"
        r = check_text("dit me may")
        assert r.decision == ModerationDecision.FLAG

    def test_leetspeak_evasion_caught(self):
        r = check_text("oh sh1t this view")
        assert r.decision == ModerationDecision.FLAG

    def test_repeated_letters_evasion_caught(self):
        r = check_text("fuuuuuck this is beautiful")
        assert r.decision == ModerationDecision.FLAG

    def test_whole_word_only_no_false_positive(self):
        # "cc" is whole-word-only → "soccer" must NOT flag
        r = check_text("I love playing soccer here every weekend")
        assert r.decision == ModerationDecision.ALLOW

    def test_whole_word_only_still_matches_alone(self):
        r = check_text("cc cái gì vậy")
        assert r.decision == ModerationDecision.FLAG


class TestSevereReject:
    def test_vietnamese_threat_rejects(self):
        r = check_text("tao giết mày bây giờ")
        assert r.decision == ModerationDecision.REJECT
        assert "severe_content" in r.reasons

    def test_english_threat_rejects(self):
        r = check_text("i will kill you if you come here")
        assert r.decision == ModerationDecision.REJECT

    def test_severe_short_circuits_other_reasons(self):
        # severe + profanity + URL → only severe_content is reported
        r = check_text("tao giết mày, đm http://spam.example")
        assert r.decision == ModerationDecision.REJECT
        assert r.reasons == ["severe_content"]


class TestContactInfoAndSpam:
    def test_vn_phone_number_flags(self):
        r = check_text("gọi mình nhé 0901 234 567")
        assert r.decision == ModerationDecision.FLAG
        assert "contact_info_phone" in r.reasons

    def test_plus84_phone_flags(self):
        r = check_text("zalo +84 901234567")
        assert "contact_info_phone" in check_text("zalo +84901234567").reasons
        assert "contact_info_phone" in r.reasons

    def test_url_flags(self):
        r = check_text("check out https://my-shop.example/sale")
        assert "contact_info_url" in r.reasons

    def test_email_flags(self):
        r = check_text("email me at someone@example.com")
        assert "contact_info_email" in r.reasons

    def test_repeat_spam_flags(self):
        r = check_text("hahaaaaaaaaaaaaaaa")
        assert "repeat_spam" in r.reasons

    def test_normal_numbers_dont_flag(self):
        r = check_text("Quán này mở từ năm 1975, giá 35000 đồng")
        assert r.decision == ModerationDecision.ALLOW


class TestPayloadModeration:
    def test_letter_text_field(self):
        r = check_payload("LETTER", {"text": "đm cuộc đời"})
        assert r.decision == ModerationDecision.FLAG

    def test_paper_plane_text_field(self):
        r = check_payload("PAPER_PLANE", {"text": "i will kill you"})
        assert r.decision == ModerationDecision.REJECT

    def test_photo_caption_checked_and_photo_held(self):
        # clean caption, but photos are FLAG by default (pending scan)
        r = check_payload("PHOTO", {"url": "s3://x.jpg", "caption": "sunset"})
        assert r.decision == ModerationDecision.FLAG
        assert "photo_pending_scan" in r.reasons

    def test_notebook_pages_each_checked(self):
        r = check_payload("NOTEBOOK", {"pages": ["nice day", "óc chó"]})
        assert r.decision == ModerationDecision.FLAG

    def test_clean_letter_allows(self):
        r = check_payload("LETTER", {"text": "Một kỷ niệm nhỏ ở Sài Gòn"})
        assert r.decision == ModerationDecision.ALLOW

    def test_enum_like_content_type_accepted(self):
        class FakeEnum:
            value = "LETTER"
        r = check_payload(FakeEnum(), {"text": "hello"})
        assert r.decision == ModerationDecision.ALLOW


class TestResultMerge:
    def test_harshest_decision_wins(self):
        a = ModerationResult(ModerationDecision.FLAG, ["profanity"])
        b = ModerationResult(ModerationDecision.REJECT, ["severe_content"])
        a.merge(b)
        assert a.decision == ModerationDecision.REJECT
        assert set(a.reasons) == {"profanity", "severe_content"}

    def test_merge_dedupes_reasons(self):
        a = ModerationResult(ModerationDecision.FLAG, ["profanity"])
        a.merge(ModerationResult(ModerationDecision.FLAG, ["profanity"]))
        assert a.reasons == ["profanity"]
