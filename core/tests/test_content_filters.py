"""Tests for content_filters: annotative markup stripping for Bible epub formats."""

import re
from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from palimpsest.ingest.content_filters import (
    PROFILE_DOUAY_RHEIMS,
    PROFILE_GENEVA,
    PROFILE_KJV,
    PROFILE_LITERARY,
    PROFILE_TYNDALE,
    ContentProfile,
    ElementSelector,
    apply_content_filters,
    detect_content_profile,
    get_profile,
    should_skip_spine_item,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


# ---------------------------------------------------------------------------
# Filter correctness tests
# ---------------------------------------------------------------------------

class TestKJVFilters:
    def test_kjv_verse_number_stripped(self):
        html = '<p><span class="verses">1</span> The book of the generation of Jesus Christ</p>'
        soup = _soup(html)
        apply_content_filters(soup, PROFILE_KJV)
        text = soup.get_text(strip=True)
        assert "1" not in text
        assert "The book of the generation of Jesus Christ" in text

    def test_kjv_red_letter_preserved(self):
        html = '<p><span class="red">Verily</span> <span class="red">I say unto you</span></p>'
        soup = _soup(html)
        apply_content_filters(soup, PROFILE_KJV)
        text = soup.get_text()
        assert "Verily" in text
        assert "I say unto you" in text

    def test_kjv_supplied_word_preserved(self):
        html = "<p>the son of <small>God</small></p>"
        soup = _soup(html)
        apply_content_filters(soup, PROFILE_KJV)
        text = soup.get_text()
        assert "the son of" in text
        assert "God" in text


class TestTyndaleFilters:
    def test_tyndale_versejump_stripped(self):
        html = '<p><span class="versejump">Matt 1 1</span> This is the boke</p>'
        soup = _soup(html)
        apply_content_filters(soup, PROFILE_TYNDALE)
        text = soup.get_text(strip=True)
        assert "Matt 1 1" not in text
        assert "versejump" not in text
        assert "This is the boke" in text

    def test_tyndale_display_reference_stripped(self):
        html = '<p><span class="displayReference">Matt 1</span> chapter content</p>'
        soup = _soup(html)
        apply_content_filters(soup, PROFILE_TYNDALE)
        text = soup.get_text(strip=True)
        assert "Matt 1" not in text
        assert "chapter content" in text


class TestGenevaFilters:
    def test_geneva_footnote_anchor_stripped(self):
        html = (
            '<p>book of the '
            '<sup class="calibre5">'
            '<a id="par_NT-BOOK001-CHAPTER001-VERSE001-FOOTNOTE001" class="calibre3">'
            '<span class="blue1">1</span></a></sup>'
            'generation</p>'
        )
        soup = _soup(html)
        apply_content_filters(soup, PROFILE_GENEVA)
        text = soup.get_text(strip=True)
        # The footnote "1" should be gone; prose words must remain
        assert "book of the" in text
        assert "generation" in text
        # Footnote digit must not appear
        assert re.search(r'\b1\b', text) is None

    def test_geneva_middlenote_stripped(self):
        html = (
            '<p>'
            '<a id="par_NT-BOOK001-CHAPTER001-MIDDLENOTE-a" class="calibre3">'
            '<span class="blue1">a</span></a>'
            ' text here</p>'
        )
        soup = _soup(html)
        apply_content_filters(soup, PROFILE_GENEVA)
        text = soup.get_text(strip=True)
        # The "a" from the middlenote anchor must be absent
        assert "text here" in text
        assert re.search(r'\ba\b', text) is None

    def test_geneva_verse_number_stripped(self):
        html = (
            '<p>'
            '<sup class="calibre5"><span class="bold1">2</span></sup>'
            ' Abraham begat Isaac'
            '</p>'
        )
        soup = _soup(html)
        apply_content_filters(soup, PROFILE_GENEVA)
        text = soup.get_text(strip=True)
        assert "2" not in text
        assert "Abraham begat Isaac" in text


class TestDouayRheimsFilters:
    def test_douay_rheims_verse_ref_stripped(self):
        # Text cleaners operate on the string content, not the DOM.
        input_text = "1:1. The book of the generation\n1:2. Abraham begot Isaac"
        expected = "The book of the generation\nAbraham begot Isaac"

        # Apply each text cleaner in order
        result = input_text
        for cleaner in PROFILE_DOUAY_RHEIMS.text_cleaners:
            result = cleaner(result)

        assert result == expected

    def test_douay_rheims_heading_promoted(self):
        html = '<div class="wQnqgsgYTu_NfSPYRkhxPg466">Matthew Chapter 1</div>'
        soup = _soup(html)
        apply_content_filters(soup, PROFILE_DOUAY_RHEIMS)
        assert soup.find("h2") is not None, "Expected the div to be promoted to <h2>"
        assert "Matthew Chapter 1" in soup.get_text()


# ---------------------------------------------------------------------------
# Profile management tests
# ---------------------------------------------------------------------------

class TestProfileManagement:
    def test_get_profile_known(self):
        profile = get_profile("bible-kjv")
        assert profile is PROFILE_KJV

    def test_get_profile_unknown(self):
        with pytest.raises(ValueError):
            get_profile("nonexistent")

    def test_literary_profile_is_noop(self):
        html = (
            '<div>'
            '<span class="note">editorial note</span>'
            '<a href="#fn1">1</a>'
            '<sup>2</sup>'
            '</div>'
        )
        soup = _soup(html)
        before = str(soup)
        apply_content_filters(soup, PROFILE_LITERARY)
        after = str(soup)
        # Nothing decomposed — the tree is structurally identical
        assert before == after


# ---------------------------------------------------------------------------
# Skip file tests
# ---------------------------------------------------------------------------

class TestSkipSpineItem:
    def _item(self, file_name: str) -> MagicMock:
        item = MagicMock()
        item.file_name = file_name
        return item

    def test_skip_file_pattern_match(self):
        item = self._item("split_003.xhtml")
        assert should_skip_spine_item(item, PROFILE_GENEVA) is True

    def test_skip_file_pattern_no_match(self):
        item = self._item("chapter_44.xhtml")
        assert should_skip_spine_item(item, PROFILE_GENEVA) is False


# ---------------------------------------------------------------------------
# Combined filter test
# ---------------------------------------------------------------------------

class TestCombinedFilters:
    def test_kjv_full_verse_cleaning(self):
        html = (
            '<h2 id="chp_401">Matthew 1</h2>'
            '<p>'
            '<span class="verses">1</span>'
            ' The book of the <span class="red">generation</span> of <small>Jesus</small> Christ,'
            ' the son of David.'
            ' <span class="verses">2</span>'
            ' Abraham begat Isaac; and Isaac begat Jacob.'
            '</p>'
        )
        soup = _soup(html)
        apply_content_filters(soup, PROFILE_KJV)

        # Check the verse paragraph body independently (the <h2> legitimately
        # contains "Matthew 1", so we scope the digit-absence check to the <p>).
        para_text = soup.find("p").get_text()

        # Verse numbers must be gone from the paragraph
        assert re.search(r'\b1\b', para_text) is None
        assert re.search(r'\b2\b', para_text) is None

        text = soup.get_text()

        # Prose content must be intact
        for word in ("generation", "Jesus", "Christ", "Abraham", "Isaac"):
            assert word in text
