from src.lab12_rag.documents import ALLOWED_DOCUMENTS, clean_text, parse_document


URL = ALLOWED_DOCUMENTS[0].url


def test_html_is_cleaned_and_title_and_section_are_extracted():
    html = """
    <html><head><title>Flow &amp; Control</title><script>ignored()</script></head>
    <body><nav>Navigation text</nav><h1>Control Flow</h1>
    <p>  First&nbsp; paragraph. </p><p>Second   paragraph.</p></body></html>
    """

    document = parse_document(URL, html)

    assert document.title == "Flow & Control"
    assert document.source == "Python documentation"
    assert document.url == URL
    assert document.text == "First paragraph.\n\nSecond paragraph."
    assert document.sections[0].title == "Control Flow"
    assert "Navigation text" not in document.text
    assert "ignored()" not in document.text


def test_plain_text_cleanup_normalizes_whitespace_and_unicode():
    assert clean_text(" A\t B\r\nC  \n\n\nD\u00a0 ") == "A B\nC\n\nD"


def test_empty_document_has_empty_text_and_no_sections():
    document = parse_document(URL, "<html><head></head><body><script>hidden</script></body></html>")

    assert document.text == ""
    assert document.sections == ()


def test_document_parser_rejects_urls_outside_the_allowlist():
    try:
        parse_document("https://example.com/not-python-docs", "<p>text</p>")
    except ValueError as error:
        assert "allowlist" in str(error)
    else:
        raise AssertionError("expected a non-allowlisted URL to be rejected")
