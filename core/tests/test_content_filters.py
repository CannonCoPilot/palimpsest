"""Tests for content_filters: annotative markup stripping for Bible epub formats."""

import re
from unittest.mock import MagicMock

import ebooklib
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
    def test_douay_rheims_verse_ref_preserved(self):
        # The DR profile intentionally KEEPS the "C:V." verse-number markers in the text:
        # the verse coordinate layer (palimpsest.verses) indexes them and the verse-number
        # mask layer hides them from analysis. Stripping them at ingest (the old behavior)
        # would destroy that index, so the DR text_cleaners must be a no-op on verse refs.
        input_text = "1:1. The book of the generation\n1:2. Abraham begot Isaac"

        result = input_text
        for cleaner in PROFILE_DOUAY_RHEIMS.text_cleaners:
            result = cleaner(result)

        assert result == input_text
        assert "1:1." in result and "1:2." in result

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


# ---------------------------------------------------------------------------
# Profile auto-detection
# ---------------------------------------------------------------------------

class TestProfileDetection:
    """Guards the detection heuristics: distinctive markup buried past the
    front matter must still be seen, marker order must prefer the most specific
    format, and KJV detection must key on the class attribute (not the bare
    word 'verses', which appears in ordinary prose)."""

    def _book(self, spine_html: list[str], title: str = "A Novel") -> MagicMock:
        book = MagicMock()
        items: dict[str, MagicMock] = {}
        spine: list[tuple[str, str]] = []
        for i, html in enumerate(spine_html):
            item = MagicMock()
            item.get_type.return_value = ebooklib.ITEM_DOCUMENT
            item.get_content.return_value = html.encode("utf-8")
            iid = f"item{i}"
            items[iid] = item
            spine.append((iid, "yes"))
        book.spine = spine
        book.get_item_with_id.side_effect = lambda iid: items.get(iid)
        book.get_metadata.side_effect = (
            lambda ns, field: [(title, {})] if (ns == "DC" and field == "title") else []
        )
        return book

    def test_marker_buried_past_front_matter_is_detected(self):
        # 15 front-matter items, then the only content item carries the marker —
        # exactly the 1599 Geneva layout that a head-only sample missed.
        spine = ["<html><body><p>front matter</p></body></html>"] * 15
        spine.append('<html><body><p class="chapter-verse">In the beginning</p></body></html>')
        book = self._book(spine, title="1599 Geneva Bible")
        assert detect_content_profile(book).name == "bible-geneva"

    def test_specific_marker_wins_over_generic(self):
        # Tyndale markup also contains verse spans; the versejump marker must
        # take precedence so it isn't mis-detected as KJV.
        html = '<html><body><span class="versejump">x</span> these verses are quoted</body></html>'
        book = self._book([html], title="Tyndale Bible New Testament")
        assert detect_content_profile(book).name == "bible-tyndale"

    def test_bare_word_verses_does_not_trigger_kjv(self):
        # The word "verses" in ordinary prose (no class) must NOT classify as KJV.
        html = "<html><body><p>He read several verses aloud by the red door.</p></body></html>"
        book = self._book([html], title="The Holy Bible, New King James Version")
        assert detect_content_profile(book).name == "literary"

    def test_verses_class_triggers_kjv(self):
        html = '<html><body><p><span class="verses">1</span> In the beginning</p></body></html>'
        book = self._book([html], title="The Holy Bible King James Version")
        assert detect_content_profile(book).name == "bible-kjv"

    def test_plain_literary_book_stays_literary(self):
        html = "<html><body><p>It was the best of times, it was the worst of times.</p></body></html>"
        book = self._book([html], title="A Tale of Two Cities")
        assert detect_content_profile(book).name == "literary"
