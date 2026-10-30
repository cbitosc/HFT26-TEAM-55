"""Unit tests for code-aware tokenizer."""

from src.backend.tokenizer import split_identifier, stem_token, tokenize


def test_split_identifier_camel_pascal():
    res1 = split_identifier("saveUploadedFile")
    assert "save" in res1
    assert "uploaded" in res1
    assert "file" in res1
    assert "saveuploadedfile" in res1

    res2 = split_identifier("StripePaymentGateway")
    assert "stripe" in res2
    assert "payment" in res2
    assert "gateway" in res2


def test_split_identifier_snake_case():
    res = split_identifier("verify_password_hash")
    assert "verify" in res
    assert "password" in res
    assert "hash" in res


def test_split_identifier_digits_and_paths():
    res = split_identifier("api/v1/auth_v2.py")
    assert "api" in res
    assert "auth" in res
    assert "v2" in res
    assert "2" in res


def test_suffix_stemming():
    assert stem_token("repositories") == "repository"
    assert stem_token("classes") == "class"
    assert stem_token("tokens") == "token"
    assert stem_token("filtering") == "filter"
    assert stem_token("extracted") == "extract"
    assert stem_token("status") == "status"  # don't strip short 'us'


def test_tokenize_query_stopwords():
    tokens = tokenize("where is login handled in the app?", remove_stopwords=True)
    # Stopwords 'where', 'is', 'in', 'the', 'handled' should be removed
    assert "login" in tokens
    assert "where" not in tokens
    assert "the" not in tokens
