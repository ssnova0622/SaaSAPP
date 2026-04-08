# test/unit/helpers/test_phone_util.py
"""Unit tests for PhoneUtil: normalization, E.164, storage, queries, and edge cases."""
from __future__ import annotations

import builtins
import re
import pytest

import app.helpers.phone_util as phone_util_module
from app.helpers.phone_util import PhoneUtil


@pytest.fixture(autouse=True)
def reset_dial_prefix_cache():
    """Isolate tests that depend on _dial_prefixes_longest_first lazy init."""
    phone_util_module._DIAL_PREFIXES_SORTED = None
    yield
    phone_util_module._DIAL_PREFIXES_SORTED = None


class TestNormalizePhoneNumber:
    def test_none_and_empty(self):
        assert PhoneUtil.normalize_phone_number(None) is None
        assert PhoneUtil.normalize_phone_number("") is None
        assert PhoneUtil.normalize_phone_number("   ") is None

    def test_non_dict_non_empty_string_returns_none(self):
        assert PhoneUtil.normalize_phone_number("+919876543210") is None

    def test_non_dict_int_returns_none(self):
        assert PhoneUtil.normalize_phone_number(9998887777) is None

    def test_canonical_dict(self):
        assert PhoneUtil.normalize_phone_number(
            {"code": "+91", "number": "9876543210"}
        ) == {"code": "+91", "number": "9876543210"}

    def test_dict_strips_and_digits_number(self):
        assert PhoneUtil.normalize_phone_number(
            {"code": "  +91 ", "number": "98765-43210"}
        ) == {"code": "+91", "number": "9876543210"}

    def test_legacy_mobile_number_key(self):
        assert PhoneUtil.normalize_phone_number(
            {"code": "+1", "mobile_number": "2025550199"}
        ) == {"code": "+1", "number": "2025550199"}

    def test_missing_code_or_number_returns_none(self):
        assert PhoneUtil.normalize_phone_number({"code": "", "number": "1234"}) is None
        assert PhoneUtil.normalize_phone_number({"code": "+91", "number": ""}) is None
        assert PhoneUtil.normalize_phone_number({"number": "1234"}) is None


class TestValidate:
    def test_valid(self):
        PhoneUtil.validate({"code": "+91", "number": "9876543210"})

    @pytest.mark.parametrize(
        "pn,msg",
        [
            ({}, "Invalid phone_number"),
            ({"code": "+91", "number": "123"}, "4–15 digits"),
            ({"code": "+91", "number": "1" * 16}, "4–15 digits"),
            ({"code": "+1234567", "number": "12345678"}, "country calling code"),
        ],
    )
    def test_invalid_raises(self, pn, msg):
        with pytest.raises(ValueError, match=re.escape(msg.split()[0]) if "phone_number" in msg else msg):
            PhoneUtil.validate(pn)


class TestToE164:
    def test_empty(self):
        assert PhoneUtil.to_e164(None) == ""
        assert PhoneUtil.to_e164({}) == ""

    def test_ok(self):
        assert PhoneUtil.to_e164({"code": "+91", "number": "9876543210"}) == "+919876543210"


class TestNormalizeE164Input:
    def test_empty(self):
        assert PhoneUtil.normalize_e164_input("", None) == ""
        assert PhoneUtil.normalize_e164_input("   ", "91") == ""

    def test_whatsapp_prefix_stripped(self):
        assert PhoneUtil.normalize_e164_input(
            "whatsapp:+919876543210", "91"
        ) == "+919876543210"

    def test_explicit_plus_uses_digits(self):
        assert PhoneUtil.normalize_e164_input("+1 202 555 0199", None) == "+12025550199"

    def test_explicit_plus_short_returns_digits_only(self):
        assert PhoneUtil.normalize_e164_input("+12345", None) == "12345"

    def test_national_prepends_default_country(self):
        assert PhoneUtil.normalize_e164_input("9876543210", None) == "+919876543210"

    def test_national_prepends_tenant_country(self):
        assert PhoneUtil.normalize_e164_input("2025550199", "1") == "+12025550199"

    def test_strip_leading_zero_when_long(self):
        assert PhoneUtil.normalize_e164_input("09876543210", "91") == "+919876543210"

    def test_cc_with_plus_in_arg(self):
        assert PhoneUtil.normalize_e164_input("9876543210", "+91") == "+919876543210"


class TestFromRaw:
    def test_india_local(self):
        assert PhoneUtil.from_raw("9876543210", "91") == {
            "code": "+91",
            "number": "9876543210",
        }

    def test_e164_us(self):
        out = PhoneUtil.from_raw("+12025550199", "1")
        assert out["code"] == "+1"
        assert out["number"] == "2025550199"

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="Invalid phone number"):
            PhoneUtil.from_raw("123", "91")

    def test_cannot_resolve_raises(self, monkeypatch):
        """No ITU prefix list and digits do not start with tenant dial → final raise."""
        monkeypatch.setattr(
            PhoneUtil,
            "_dial_prefixes_longest_first",
            classmethod(lambda cls: []),
        )
        with pytest.raises(ValueError, match="Could not determine country"):
            PhoneUtil.from_raw("+919876543210", "1")

    def test_tenant_dial_fallback_when_prefix_list_empty(self, monkeypatch):
        """After exhausting ITU prefixes, parse using tenant dial + national digits."""
        monkeypatch.setattr(
            PhoneUtil,
            "_dial_prefixes_longest_first",
            classmethod(lambda cls: []),
        )
        assert PhoneUtil.from_raw("+919876543210", "91") == {
            "code": "+91",
            "number": "9876543210",
        }

    def test_prefix_match_skips_when_national_too_short_then_succeeds(self):
        """1264 match leaves 3-digit national → continue; shorter ITU prefix then parses."""
        assert PhoneUtil.from_raw("+1264123", "1") == {"code": "+1", "number": "264123"}


class TestPrepareStorage:
    def test_none_blank(self):
        assert PhoneUtil.prepare_storage(None, "91") is None
        assert PhoneUtil.prepare_storage("  ", "91") is None

    def test_valid(self):
        pn = PhoneUtil.prepare_storage("9876543210", "91")
        assert pn == {"code": "+91", "number": "9876543210"}


class TestPromoNormalize:
    def test_whatsapp_plus_form(self):
        assert PhoneUtil.promo_normalize("whatsapp:+919876543210") == "+919876543210"

    def test_spaces_hyphens(self):
        assert PhoneUtil.promo_normalize(" +91 987 654 3210 ") == "+919876543210"


class TestTenantDefaultDialDigits:
    def test_none_uses_default_iso(self):
        d = PhoneUtil.tenant_default_dial_digits(None)
        assert d == PhoneUtil.tenant_default_dial_digits("IN")

    def test_us(self):
        assert PhoneUtil.tenant_default_dial_digits("US") == "1"


class TestDialPrefixesLongestFirst:
    def test_cached_singleton(self):
        phone_util_module._DIAL_PREFIXES_SORTED = None
        a = PhoneUtil._dial_prefixes_longest_first()
        b = PhoneUtil._dial_prefixes_longest_first()
        assert a is b
        assert all(isinstance(x, str) for x in a)
        assert a == sorted(a, key=len, reverse=True)


class TestDigits:
    def test_strips_non_digits(self):
        assert PhoneUtil.digits("a+91 (987) 654-3210 b") == "919876543210"
        assert PhoneUtil.digits("") == ""


class TestCustomerFilter:
    def test_ok(self):
        q = PhoneUtil.customer_filter("t1", {"code": "+91", "number": "9876543210"})
        assert q == {
            "tenant": "t1",
            "phone_number.code": "+91",
            "phone_number.number": "9876543210",
        }

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="phone_number required"):
            PhoneUtil.customer_filter("t1", {})


class TestEnrichDocument:
    def test_strips_legacy_phone_and_sets_canonical(self):
        doc = {"id": "1", "phone": "9876543210", "phone_number": None}
        out = PhoneUtil.enrich_document(doc, tenant_dial_digits="91")
        assert "phone" not in out
        assert out["phone_number"] == {"code": "+91", "number": "9876543210"}

    def test_legacy_invalid_keeps_no_phone_number(self):
        doc = {"id": "1", "phone": "x", "phone_number": None}
        out = PhoneUtil.enrich_document(doc, tenant_dial_digits="91")
        assert "phone_number" not in out

    def test_custom_phone_field_and_legacy_plain(self):
        doc = {"customer_phone_number": None, "legacy_mobile": "+12025550199"}
        out = PhoneUtil.enrich_document(
            doc,
            phone_field="customer_phone_number",
            tenant_dial_digits="1",
            legacy_plain_field="legacy_mobile",
        )
        assert out["customer_phone_number"]["code"] == "+1"
        assert out["customer_phone_number"]["number"] == "2025550199"
        assert "legacy_mobile" not in out

    def test_invalid_struct_removed(self):
        doc = {"phone_number": {"code": "", "number": ""}}
        out = PhoneUtil.enrich_document(doc, tenant_dial_digits="91")
        assert "phone_number" not in out


class TestExportE164:
    def test_flat_pn(self):
        assert PhoneUtil.export_e164({"code": "+91", "number": "9" * 10}, "91") == "+91" + "9" * 10

    def test_doc_phone_number(self):
        assert PhoneUtil.export_e164(
            {"phone_number": {"code": "+91", "number": "9876543210"}}, "1"
        ) == "+919876543210"

    def test_doc_customer_phone_number(self):
        assert PhoneUtil.export_e164(
            {"customer_phone_number": {"code": "+1", "number": "2025550199"}}, "91"
        ) == "+12025550199"

    def test_fallback_string(self):
        assert PhoneUtil.export_e164("9876543210", "91") == "+919876543210"

    def test_falsy(self):
        assert PhoneUtil.export_e164(None, "91") == ""


class TestAppointmentCustomerE164:
    def test_prefers_customer_phone_number(self):
        assert (
            PhoneUtil.appointment_customer_e164(
                {
                    "customer_phone_number": {"code": "+91", "number": "1111111111"},
                    "customer_phone": "9999999999",
                },
                "91",
            )
            == "+911111111111"
        )

    def test_legacy_customer_phone(self):
        assert (
            PhoneUtil.appointment_customer_e164(
                {"customer_phone": "9876543210"},
                "91",
            )
            == "+919876543210"
        )

    def test_empty(self):
        assert PhoneUtil.appointment_customer_e164({}, "91") == ""


class TestCustomerMatchQuery:
    def test_empty_phone_returns_impossible_match(self):
        q = PhoneUtil.customer_match_query("t1", "", "91")
        assert q == {"tenant": "t1", "_id": None}

    def test_or_when_canonical_resolved(self):
        q = PhoneUtil.customer_match_query("t1", "+919876543210", "91")
        assert "$or" in q
        assert len(q["$or"]) == 2

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            PhoneUtil.customer_match_query("t1", "not-a-valid-phone!!!", "91")


class TestAppointmentPhoneSearchQuery:
    def test_plus_numeric_digits_int_clause_branch(self):
        q = PhoneUtil.appointment_phone_search_query("t1", "+919876543210", "91")
        assert "$or" in q
        clauses = q["$or"]
        assert any("customer_phone_number.code" in c for c in clauses)
        assert any(c.get("customer_phone") == 919876543210 for c in clauses)

    def test_plus_branch_falls_back_to_regex_when_int_conversion_fails(self):
        """If int(digits) raises, only regex clause is added for numeric-looking +values."""
        orig_int = builtins.int

        def _int(*args, **kwargs):
            if (
                len(args) == 1
                and not kwargs
                and isinstance(args[0], str)
                and args[0] == "919876543210"
            ):
                raise ValueError("not an int")
            return orig_int(*args, **kwargs)

        try:
            builtins.int = _int
            q = PhoneUtil.appointment_phone_search_query("t1", "+919876543210", "91")
        finally:
            builtins.int = orig_int
        assert "$or" in q
        assert all(not isinstance(c.get("customer_phone"), int) for c in q["$or"])

    def test_no_plus_branch(self):
        q = PhoneUtil.appointment_phone_search_query("t1", "9876543210", "91")
        assert "$or" in q

    def test_empty_search_still_structured(self):
        q = PhoneUtil.appointment_phone_search_query("t1", "", "91")
        assert "$or" in q or "customer_phone" in q

    def test_plus_branch_second_from_raw_uses_val_when_search_raw_invalid(self, monkeypatch):
        """When from_raw(search_raw) fails, retry with normalized val (still +prefixed)."""
        real_norm = PhoneUtil.normalize_e164_input
        real_from_raw = PhoneUtil.from_raw

        def norm_side_effect(phone, country_code_digits=None):
            if phone == "bad-raw-plus":
                return "+919876543210"
            return real_norm(phone, country_code_digits)

        def from_raw_side_effect(raw, td):
            if raw == "bad-raw-plus":
                raise ValueError("bad")
            return real_from_raw(raw, td)

        monkeypatch.setattr(PhoneUtil, "normalize_e164_input", staticmethod(norm_side_effect))
        monkeypatch.setattr(PhoneUtil, "from_raw", classmethod(lambda cls, r, td: from_raw_side_effect(r, td)))
        q = PhoneUtil.appointment_phone_search_query("t1", "bad-raw-plus", "91")
        assert "$or" in q
        assert any(
            c.get("customer_phone_number.number") == "9876543210"
            for c in q["$or"]
        )

    def test_else_branch_adds_structured_phone_when_normalized_local_digits(self, monkeypatch):
        """Non-+ val path: canonical match when national digits normalize to full number."""
        real = PhoneUtil.normalize_e164_input

        def norm_local(phone, country_code_digits=None):
            if str(phone).strip() == "local-search-token":
                return "919876543210"
            return real(phone, country_code_digits)

        monkeypatch.setattr(PhoneUtil, "normalize_e164_input", staticmethod(norm_local))
        q = PhoneUtil.appointment_phone_search_query("t1", "local-search-token", "91")
        assert "$or" in q
        assert any(
            c.get("customer_phone_number.code") == "+91"
            and c.get("customer_phone_number.number") == "9876543210"
            for c in q["$or"]
        )

    def test_plus_branch_both_from_raw_attempts_fail(self, monkeypatch):
        """Inner ValueError when both search_raw and val fail to parse to canonical phone."""
        real_norm = PhoneUtil.normalize_e164_input

        def norm_side_effect(phone, country_code_digits=None):
            if phone == "unparseable-token":
                return "+919876543210"
            return real_norm(phone, country_code_digits)

        def from_raw_always_fail(raw, td):
            raise ValueError("no parse")

        monkeypatch.setattr(PhoneUtil, "normalize_e164_input", staticmethod(norm_side_effect))
        monkeypatch.setattr(
            PhoneUtil,
            "from_raw",
            classmethod(lambda cls, r, td: from_raw_always_fail(r, td)),
        )
        q = PhoneUtil.appointment_phone_search_query("t1", "unparseable-token", "91")
        assert "$or" in q
        assert not any("customer_phone_number.code" in c for c in q["$or"])
