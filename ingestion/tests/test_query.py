from query import build_prompt, format_sources, build_filter


def make_chunk(**kwargs) -> dict:
    defaults = {
        "text": "The batter shall be called out.",
        "governing_body": "DYB",
        "source_doc": "2026-DYB-Official-Playing-Rules",
    }
    return {**defaults, **kwargs}


class TestBuildPrompt:
    def test_contains_question(self):
        prompt = build_prompt("What is the infield fly rule?", [make_chunk()])
        assert "What is the infield fly rule?" in prompt

    def test_contains_chunk_text(self):
        chunk = make_chunk(text="The infield fly rule applies when...")
        prompt = build_prompt("What is the infield fly rule?", [chunk])
        assert "The infield fly rule applies when..." in prompt

    def test_labels_governing_body(self):
        prompt = build_prompt("question", [make_chunk(governing_body="OBR")])
        assert "OBR" in prompt

    def test_includes_rule_number_when_present(self):
        prompt = build_prompt("question", [make_chunk(rule_number="6.01")])
        assert "6.01" in prompt

    def test_omits_rule_number_label_when_absent(self):
        chunk = make_chunk()  # no rule_number key
        prompt = build_prompt("question", [chunk])
        assert "Rule None" not in prompt

    def test_includes_section_title_when_present(self):
        prompt = build_prompt("question", [make_chunk(section_title="THE BATTER")])
        assert "THE BATTER" in prompt

    def test_numbers_multiple_sources(self):
        chunks = [make_chunk(), make_chunk(governing_body="OBR")]
        prompt = build_prompt("question", chunks)
        assert "Source 1" in prompt
        assert "Source 2" in prompt

    def test_empty_chunks_still_includes_question(self):
        prompt = build_prompt("What is a balk?", [])
        assert "What is a balk?" in prompt


class TestFormatSources:
    def test_includes_governing_body(self):
        result = format_sources([make_chunk(governing_body="NFHS_SOFTBALL")])
        assert "NFHS_SOFTBALL" in result

    def test_includes_rule_number_when_present(self):
        result = format_sources([make_chunk(rule_number="1-1-3")])
        assert "1-1-3" in result

    def test_includes_page_when_present(self):
        result = format_sources([make_chunk(page_number=42)])
        assert "42" in result

    def test_omits_page_when_absent(self):
        result = format_sources([make_chunk()])
        assert "p.None" not in result

    def test_multiple_sources_each_on_own_line(self):
        chunks = [make_chunk(), make_chunk(governing_body="OBR")]
        result = format_sources(chunks)
        assert result.count("\n") >= 1


class TestBuildFilter:
    def test_none_returns_none(self):
        assert build_filter(None) is None

    def test_standalone_body_uses_eq(self):
        f = build_filter("DYB")
        assert f == {"governing_body": {"$eq": "DYB"}}

    def test_obr_uses_eq(self):
        f = build_filter("OBR")
        assert f == {"governing_body": {"$eq": "OBR"}}

    def test_nfhs_softball_uses_eq(self):
        f = build_filter("NFHS_SOFTBALL")
        assert f == {"governing_body": {"$eq": "NFHS_SOFTBALL"}}

    def test_dys_includes_nfhs_softball(self):
        f = build_filter("DYS")
        assert f == {"governing_body": {"$in": ["DYS", "NFHS_SOFTBALL"]}}

    def test_dys_filter_contains_both_bodies(self):
        f = build_filter("DYS")
        bodies = f["governing_body"]["$in"]
        assert "DYS" in bodies
        assert "NFHS_SOFTBALL" in bodies
