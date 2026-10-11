from src.lab12_rag.chunking import chunk_document, chunk_text
from src.lab12_rag.documents import DocumentRecord, DocumentSection


def _document(text: str = "abcdefghij") -> DocumentRecord:
    return DocumentRecord(
        doc_id="doc-1",
        source="Python documentation",
        title="Sample page",
        url="https://docs.python.org/3/tutorial/controlflow.html",
        text=text,
        sections=(DocumentSection("Example section", text),),
    )


def test_chunk_boundaries_and_overlap_are_deterministic():
    chunks = chunk_text("abcdefghij", chunk_size=4, overlap=1)

    assert chunks == [("abcd", 0, 4), ("defg", 3, 7), ("ghij", 6, 10)]


def test_short_document_produces_one_chunk():
    assert chunk_text(" short text ", chunk_size=10, overlap=2) == [
        ("short text", 0, 10)
    ]


def test_empty_text_produces_no_chunks():
    assert chunk_text(" \n\t ", chunk_size=10, overlap=2) == []


def test_chunk_ids_are_stable_and_metadata_is_preserved():
    first = chunk_document(_document(), chunk_size=4, overlap=1)
    second = chunk_document(_document(), chunk_size=4, overlap=1)

    assert first == second
    assert len({chunk.chunk_id for chunk in first}) == 3
    assert first[0].doc_id == "doc-1"
    assert first[0].source == "Python documentation"
    assert first[0].title == "Sample page"
    assert first[0].url == "https://docs.python.org/3/tutorial/controlflow.html"
    assert first[0].section == "Example section"
    assert first[0].chunk_index == 0


def test_chunking_rejects_invalid_size_and_overlap():
    for size, overlap in ((0, 0), (4, -1), (4, 4)):
        try:
            chunk_text("text", chunk_size=size, overlap=overlap)
        except ValueError:
            pass
        else:
            raise AssertionError("expected invalid chunk settings to be rejected")
