"""Unit tests for handcrafted BM25F inverted index and ranking engine."""

from src.backend.inverted_index import FieldAwareIndex
from src.backend.models import CodeChunk
from src.backend.ranker import rank_lexical


def test_index_and_rank_bm25f(tmp_path):
    index = FieldAwareIndex("test_session", data_dir=tmp_path)

    c1 = CodeChunk(
        id="c1",
        path="auth/login.py",
        language="python",
        kind="function",
        symbol="login_user",
        parent=None,
        start_line=10,
        end_line=20,
        code="def login_user(email, password):\n    session = authenticate(email, password)\n    return session",
        docstring="Authenticate user credentials and create session.",
        imports=["auth.tokens"],
    )

    c2 = CodeChunk(
        id="c2",
        path="payments/refund.py",
        language="python",
        kind="function",
        symbol="process_refund",
        parent=None,
        start_line=15,
        end_line=25,
        code="def process_refund(order_id, amount):\n    return execute_refund(order_id)",
        docstring="Process customer refund request.",
        imports=[],
    )

    index.add_chunk(c1)
    index.add_chunk(c2)
    index.finalize()

    # Query for login
    results, terms = rank_lexical("where is login handled?", index, top_k=5)
    assert len(results) > 0
    top = results[0]
    assert top.chunk_id == "c1"
    assert top.symbol == "login_user"
    assert any("Symbol Match" in b for b in top.breakdown.boosts_applied)
    assert top.evidence_id == "E1"

    # Query for refund
    results_refund, _ = rank_lexical("how are customer refunds processed?", index, top_k=5)
    assert len(results_refund) > 0
    assert results_refund[0].chunk_id == "c2"


def test_index_persistence(tmp_path):
    index = FieldAwareIndex("persist_session", data_dir=tmp_path)
    c = CodeChunk(
        id="c1",
        path="main.py",
        language="python",
        kind="function",
        symbol="start_server",
        parent=None,
        start_line=1,
        end_line=5,
        code="def start_server(): pass",
        docstring="Start HTTP server",
        imports=[],
    )
    index.add_chunk(c)
    index.finalize()
    index.save_to_disk()

    # Load from disk
    loaded = FieldAwareIndex.load_from_disk("persist_session", data_dir=tmp_path)
    assert loaded is not None
    assert loaded.total_docs == 1
    assert "start_server" in loaded.chunks["c1"].symbol
