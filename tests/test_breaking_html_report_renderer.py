"""
test_html_report_renderer — Unit tests for HtmlContractDiffRenderer
------------------------------------------------------------------
Test classes:
    TestHtmlEscape       — _e(): HTML escaping
    TestFormatValue      — _format_value(): dict summary, truncation, escaping
    TestPill             — _pill(): change-type pill markup
    TestPathTd           — _path_td(): depth indentation and list-item prefix
    TestRenderDetailRows — _render_detail_rows(): ancestor inference, sorting, values
    TestGoldenHtml       — exact structural golden-file comparison (style stripped)
"""

import os
import re

from datacontract.breaking.html_report_renderer import (
    _e,
    _format_value,
    _path_td,
    _pill,
    _render_detail_rows,
)

# ---------------------------------------------------------------------------
# _e
# ---------------------------------------------------------------------------


class TestHtmlEscape:
    def test_escapes_angle_brackets(self):
        assert _e("<b>") == "&lt;b&gt;"

    def test_escapes_ampersand(self):
        assert _e("a & b") == "a &amp; b"

    def test_passes_plain_string(self):
        assert _e("hello") == "hello"

    def test_converts_non_string(self):
        assert _e(42) == "42"


# ---------------------------------------------------------------------------
# _format_value
# ---------------------------------------------------------------------------


class TestFormatValue:
    def test_none_returns_empty(self):
        assert _format_value(None) == ""

    def test_plain_string(self):
        assert _format_value("hello") == "hello"

    def test_dict_shows_key_summary(self):
        result = _format_value({"a": 1, "b": 2})
        assert "a" in result
        assert "b" in result
        assert "obj" in result  # CSS class

    def test_dict_with_more_than_4_keys_truncates(self):
        result = _format_value({"a": 1, "b": 2, "c": 3, "d": 4, "e": 5})
        assert "..." in result

    def test_long_string_not_truncated(self):
        long = "x" * 200
        result = _format_value(long)
        assert "…" not in result
        assert len(result) == 200

    def test_html_escapes_value(self):
        result = _format_value("<script>")
        assert "&lt;script&gt;" in result


# ---------------------------------------------------------------------------
# _pill
# ---------------------------------------------------------------------------


class TestPill:
    def test_added(self):
        result = _pill("added")
        assert "Added" in result
        assert 'class="pill added"' in result

    def test_removed(self):
        result = _pill("removed")
        assert "Removed" in result
        assert 'class="pill removed"' in result

    def test_changed(self):
        result = _pill("changed")
        assert "Changed" in result
        assert 'class="pill changed"' in result

    def test_unknown_type_capitalised(self):
        result = _pill("deprecated")
        assert "Deprecated" in result


# ---------------------------------------------------------------------------
# _path_td
# ---------------------------------------------------------------------------


class TestPathTd:
    def test_depth_zero_no_indent(self):
        result = _path_td("schema", 0, False)
        assert "padding-left:calc(14px + 0ch)" in result

    def test_depth_adds_padding(self):
        result = _path_td("orders", 2, False)
        assert "4ch" in result

    def test_list_item_prefix(self):
        result = _path_td("orders", 1, True)
        assert "- orders" in result

    def test_non_list_item_no_prefix(self):
        result = _path_td("orders", 1, False)
        assert "- " not in result


# ---------------------------------------------------------------------------
# _render_detail_rows
# ---------------------------------------------------------------------------


class TestRenderDetailRows:
    def test_empty_changes(self):
        assert _render_detail_rows([]) == []

    def test_single_added_row(self):
        rows = _render_detail_rows([{"path": "schema.orders", "changeType": "Added"}])
        assert any("orders" in r for r in rows)
        assert any("Added" in r for r in rows)

    def test_ancestor_rows_inferred(self):
        rows = _render_detail_rows(
            [
                {
                    "path": "schema.orders.properties.amount",
                    "changeType": "Added",
                }
            ]
        )
        combined = "\n".join(rows)
        assert "schema" in combined
        assert "orders" in combined
        assert "amount" in combined

    def test_list_item_prefix_for_list_container_children(self):
        rows = _render_detail_rows([{"path": "schema.orders", "changeType": "Added"}])
        assert any("- orders" in r for r in rows)

    def test_changed_row_includes_old_and_new(self):
        rows = _render_detail_rows(
            [
                {
                    "path": "slaProperties.availability.value",
                    "changeType": "Changed",
                    "old_value": "99.9%",
                    "new_value": "99.5%",
                }
            ]
        )
        combined = "\n".join(rows)
        assert "99.9%" in combined
        assert "99.5%" in combined

    def test_rows_sorted_by_path(self):
        rows = _render_detail_rows(
            [
                {"path": "schema.orders", "changeType": "Removed"},
                {"path": "schema.customers", "changeType": "Added"},
            ]
        )
        combined = "\n".join(rows)
        assert combined.index("customers") < combined.index("orders")


# ---------------------------------------------------------------------------
# Golden output — exact structural match (style block stripped)
# ---------------------------------------------------------------------------

_GOLDEN_DIFF = {
    "dictionary_item_added": {
        "root['schema']['customers']": {
            "physicalName": "customers_tbl",
            "properties": {
                "customer_id": {"logicalType": "string", "required": True},
            },
        }
    },
    "dictionary_item_removed": {
        "root['schema']['orders']['properties']['customer_id']": {
            "logicalType": "string",
            "required": True,
        }
    },
    "values_changed": {
        "root['slaProperties']['availability']['value']": {
            "old_value": "99.9%",
            "new_value": "99.5%",
        }
    },
}


def _golden_report_data():
    from datacontract.breaking.report_renderer import ContractDiffReport

    return ContractDiffReport().build_report_data(_GOLDEN_DIFF, source_label="v1.yaml", target_label="v2.yaml")


def _strip_style(html: str) -> str:
    return re.sub(r"<style>.*?</style>", "<style>...</style>", html, flags=re.DOTALL)


class TestGoldenHtml:
    FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "breaking", "unit")
    FIXED_TS = "2025-01-01 00:00:00 UTC"

    def test_exact_html_structure(self):
        from unittest.mock import patch

        from datacontract.breaking.html_report_renderer import HtmlContractDiffRenderer

        golden_path = os.path.join(self.FIXTURE_DIR, "golden_html.html")
        expected = open(golden_path).read()
        with patch("datacontract.breaking.report_renderer.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = self.FIXED_TS
            rd = _golden_report_data()
        actual = _strip_style(HtmlContractDiffRenderer(report_data=rd).render())
        assert actual == expected, (
            f"HTML renderer structural output has changed. If intentional, regenerate {golden_path}"
        )
