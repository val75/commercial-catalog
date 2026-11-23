from __future__ import annotations

import pytest

from redact_quote import find_leftovers, parse_names, redact, run

NAMES = {
    "VENDOR_A": ["Northwind Traders Inc", "Northwind"],
    "CUSTOMER_A": ["Contoso Ltd"],
}


# --- names file ---------------------------------------------------------------


def test_parse_names_groups_spellings_by_placeholder():
    text = "VENDOR_A = Northwind Traders Inc\nVENDOR_A = Northwind\nCUSTOMER_A = Contoso Ltd\n"
    assert parse_names(text) == NAMES


def test_parse_names_ignores_comments_and_blank_lines():
    text = "# VENDOR_A = Example Vendor Inc\n\nVENDOR_A = Northwind\n"
    assert parse_names(text) == {"VENDOR_A": ["Northwind"]}


def test_parse_names_with_only_comments_is_an_error():
    # Otherwise an unfilled stub would "succeed" with nothing redacted.
    with pytest.raises(ValueError):
        parse_names("# VENDOR_A = Example Vendor Inc\n")


@pytest.mark.parametrize(
    "line",
    [
        "Secret Company Inc",            # no separator
        "lowercase = Secret Company",    # placeholder would not be recognisable
        "VENDOR_A = ?!",                 # nothing to match on
        "VENDOR_A = S",                  # too short to match safely
    ],
)
def test_parse_names_errors_give_the_line_number_but_not_the_content(line):
    with pytest.raises(ValueError) as exc:
        parse_names(f"# comment\n{line}\n")
    assert "line 2" in str(exc.value)
    assert "Secret" not in str(exc.value)


# --- name replacement ---------------------------------------------------------


def test_redact_replaces_a_name_with_its_placeholder():
    assert redact("Issued by Northwind today", NAMES).text == "Issued by VENDOR_A today"


def test_redact_ignores_capitalization():
    assert redact("NORTHWIND and northwind", NAMES).text == "VENDOR_A and VENDOR_A"


def test_redact_handles_a_name_split_across_lines():
    assert redact("To: Contoso\nLtd\nRef 12", NAMES).text == "To: CUSTOMER_A\nRef 12"


def test_redact_handles_punctuation_between_words_of_a_name():
    assert redact("Contoso-Ltd", NAMES).text == "CUSTOMER_A"


def test_redact_replaces_the_longest_spelling_first():
    # A partial match would leave "VENDOR_A Traders Inc" behind.
    assert redact("Northwind Traders Inc", NAMES).text == "VENDOR_A"


def test_redact_leaves_words_that_only_contain_a_name_for_the_leftover_check():
    assert redact("Northwindish", NAMES).text == "Northwindish"


def test_redact_handles_ligatures_from_pdf_extraction():
    names = {"VENDOR_A": ["Unified Systems"]}
    assert redact("Uniﬁed Systems", names).text == "VENDOR_A"


def test_redact_counts_replacements_per_placeholder():
    result = redact("Northwind, Northwind Traders Inc, Contoso Ltd", NAMES)
    assert result.counts["VENDOR_A"] == 2
    assert result.counts["CUSTOMER_A"] == 1


def test_redact_reports_zero_for_a_placeholder_that_never_matched():
    assert redact("nothing here", NAMES).counts == {
        "VENDOR_A": 0,
        "CUSTOMER_A": 0,
        "[EMAIL]": 0,
        "[URL]": 0,
        "[PHONE]": 0,
    }


# --- contact details ----------------------------------------------------------


def test_redact_blanks_emails():
    assert redact("Mail sales.team+q@mail.acme-corp.co.uk now", {}).text == "Mail [EMAIL] now"


@pytest.mark.parametrize(
    "url",
    ["https://acme.example/quotes?id=1", "http://acme.example", "www.acme.example", "acme-corp.com"],
)
def test_redact_blanks_urls_and_bare_domains(url):
    assert redact(f"See {url} for terms", {}).text == "See [URL] for terms"


def test_redact_keeps_table_cell_borders_next_to_a_url():
    assert redact("| https://acme.example| next |", {}).text == "| [URL]| next |"


@pytest.mark.parametrize(
    "phone",
    ["(555) 019-2284", "555-019-2284", "555.019.2284", "+44 20 7946 0958", "+1 (555) 019-2284"],
)
def test_redact_blanks_phone_numbers(phone):
    assert redact(f"Call {phone} today", {}).text == "Call [PHONE] today"


def test_redact_blanks_a_labelled_number_in_any_format():
    assert redact("Mobile: 020 7946 0958", {}).text == "Mobile: [PHONE]"


@pytest.mark.parametrize(
    "text",
    [
        "Unit price: $14,280",
        "Quote #: DF-Q-88214",
        "Option Kit 338-CHQX",
        "Date 2026-07-29",
        "2x Intel Xeon Gold 6438N 32C 2.0GHz",
        "6x 3.84TB NVMe U.2",
        "| 16 | 32 | 64 | 128 | 256 |",
        "16 32 64 128 256 512 1024",
    ],
)
def test_redact_keeps_prices_part_numbers_and_specs(text):
    assert redact(text, {}).text == text


# --- leftover check -----------------------------------------------------------


def test_find_leftovers_is_empty_when_a_name_is_gone():
    assert find_leftovers("Issued by VENDOR_A", NAMES) == []


def test_find_leftovers_catches_a_name_joined_to_another_word():
    leftovers = find_leftovers("line one\nNorthwindish here", NAMES)
    assert [(item.placeholder, item.line) for item in leftovers] == [("VENDOR_A", 2)]


def test_find_leftovers_catches_a_name_with_spaces_inside_it():
    assert find_leftovers("N o r t h w i n d", NAMES)[0].placeholder == "VENDOR_A"


def test_find_leftovers_catches_a_name_with_accents():
    assert find_leftovers("Nórthwind", NAMES)[0].placeholder == "VENDOR_A"


def test_find_leftovers_catches_a_name_with_a_zero_width_character():
    assert find_leftovers("North​wind", NAMES)[0].placeholder == "VENDOR_A"


def test_find_leftovers_does_not_flag_placeholders():
    # The name "Vendor" must not match the placeholder that replaced it.
    assert find_leftovers("VENDOR_A [EMAIL]", {"VENDOR_A": ["Vendor"], "CUSTOMER_A": ["Email"]}) == []


def test_find_leftovers_does_not_join_text_across_a_placeholder():
    assert find_leftovers("North VENDOR_A wind", NAMES) == []


# --- run: the command-line workflow -------------------------------------------


@pytest.fixture
def workspace(tmp_path):
    names = tmp_path / "names.txt"
    names.write_text("VENDOR_A = Northwind\nCUSTOMER_A = Contoso Ltd\n", encoding="utf-8")
    quote = tmp_path / "northwind-for-contoso.csv"
    quote.write_text(
        "Item,Qty\nNorthwind R660 for Contoso Ltd,8\nContact sales@northwind.example,1\n",
        encoding="utf-8",
    )
    return tmp_path, quote, names, tmp_path / "out.md"


def test_run_writes_the_redacted_markdown(workspace):
    _, quote, names, out = workspace
    assert run(quote, names, out) == 0
    written = out.read_text(encoding="utf-8")
    assert "VENDOR_A R660 for CUSTOMER_A" in written
    assert "[EMAIL]" in written
    assert "northwind" not in written.lower()
    assert "contoso" not in written.lower()


def test_run_output_does_not_contain_the_original_filename(workspace):
    tmp_path, quote, names, out = workspace
    renamed = tmp_path / "secret-filename.csv"
    quote.rename(renamed)
    assert run(renamed, names, out) == 0
    assert "secret-filename" not in out.read_text(encoding="utf-8")


def test_run_terminal_output_shows_counts_but_no_private_text(workspace, capsys):
    _, quote, names, out = workspace
    run(quote, names, out)
    printed = capsys.readouterr()
    combined = (printed.out + printed.err).lower()
    assert "vendor_a: 1" in combined
    assert "northwind" not in combined
    assert "contoso" not in combined


def test_run_stops_without_writing_when_a_name_remains(workspace, capsys):
    tmp_path, _, names, out = workspace
    quote = tmp_path / "quote.csv"
    quote.write_text("Item\nNorthwindish server\n", encoding="utf-8")
    assert run(quote, names, out) == 1
    assert not out.exists()
    printed = capsys.readouterr()
    combined = (printed.out + printed.err).lower()
    assert "vendor_a" in combined
    assert "line" in combined
    assert "northwind" not in combined


def test_run_keeps_a_separately_named_copy_for_checking_the_reported_lines(workspace):
    tmp_path, _, names, out = workspace
    quote = tmp_path / "quote.csv"
    quote.write_text("Item\nNorthwindish server\n", encoding="utf-8")
    run(quote, names, out)
    assert "Northwindish" in (tmp_path / "out.needs-review.md").read_text(encoding="utf-8")


def test_run_removes_the_review_copy_once_the_check_passes(workspace):
    tmp_path, quote, names, out = workspace
    review = tmp_path / "out.needs-review.md"
    review.write_text("stale", encoding="utf-8")
    assert run(quote, names, out) == 0
    assert not review.exists()


def test_run_hides_an_ingestion_warning_that_contains_a_name(workspace, capsys, monkeypatch):
    import redact_quote
    from ingestion import NormalizedDoc, SourceType

    tmp_path, quote, names, out = workspace
    doc = NormalizedDoc(
        source_type=SourceType.EXCEL,
        source_name="quote.xlsx",
        markdown="Item",
        warnings=["Sheet 'Northwindish' had no data; skipped."],
    )
    monkeypatch.setattr(redact_quote, "ingest_file", lambda data, filename: doc)
    assert run(quote, names, out) == 0
    assert "northwind" not in capsys.readouterr().out.lower()


def test_run_removes_output_from_an_earlier_run_when_it_stops(workspace):
    tmp_path, _, names, out = workspace
    out.write_text("stale", encoding="utf-8")
    quote = tmp_path / "quote.csv"
    quote.write_text("Item\nNorthwindish server\n", encoding="utf-8")
    assert run(quote, names, out) == 1
    assert not out.exists()


def test_run_can_allow_a_checked_line_after_a_false_alarm(workspace):
    tmp_path, _, names, out = workspace
    quote = tmp_path / "quote.csv"
    quote.write_text("Item\nNorthwindish server\n", encoding="utf-8")
    assert run(quote, names, out) == 1
    line = next(
        item.line
        for item in find_leftovers(redact(_markdown_of(quote), parse_names(names.read_text())).text, parse_names(names.read_text()))
    )
    assert run(quote, names, out, allowed_lines={line}) == 0
    assert out.exists()


def test_run_treats_an_empty_document_as_an_error(workspace):
    tmp_path, _, names, out = workspace
    quote = tmp_path / "empty.csv"
    quote.write_text("", encoding="utf-8")
    assert run(quote, names, out) == 1
    assert not out.exists()


def test_run_errors_on_an_unfilled_names_file(workspace):
    tmp_path, quote, _, out = workspace
    names = tmp_path / "stub.txt"
    names.write_text("# VENDOR_A = Example Vendor Inc\n", encoding="utf-8")
    assert run(quote, names, out) == 1
    assert not out.exists()


def test_run_error_for_an_unsupported_file_does_not_print_its_name(workspace, capsys):
    tmp_path, _, names, out = workspace
    quote = tmp_path / "northwind-quote.docx"
    quote.write_bytes(b"not really a docx")
    assert run(quote, names, out) == 1
    printed = capsys.readouterr()
    assert "northwind" not in (printed.out + printed.err).lower()


def test_run_error_for_a_missing_file_does_not_print_its_name(workspace, capsys):
    tmp_path, _, names, out = workspace
    assert run(tmp_path / "northwind-missing.pdf", names, out) == 1
    printed = capsys.readouterr()
    assert "northwind" not in (printed.out + printed.err).lower()


def test_run_redacts_an_xlsx_including_sheet_titles_hidden_sheets_and_split_cells(workspace):
    from openpyxl import Workbook

    tmp_path, _, names, out = workspace
    wb = Workbook()
    visible = wb.active
    visible.title = "Northwind BOM"
    visible.append(["Part", "Qty"])
    visible.append(["Intel Xeon Gold 6438N", 2])
    visible.append(["Contoso", "Ltd"])
    hidden = wb.create_sheet("Internal")
    hidden.sheet_state = "hidden"
    hidden.append(["Prepared for Contoso Ltd"])
    quote = tmp_path / "quote.xlsx"
    wb.save(quote)

    assert run(quote, names, out) == 0
    written = out.read_text(encoding="utf-8")
    assert "## Sheet: VENDOR_A BOM" in written
    assert "Intel Xeon Gold 6438N" in written
    assert "Prepared for CUSTOMER_A" in written  # hidden sheets are included
    assert "northwind" not in written.lower()
    assert "contoso" not in written.lower()


def _markdown_of(quote):
    from ingestion import ingest_file

    return ingest_file(quote.read_bytes(), f"quote{quote.suffix}").markdown
