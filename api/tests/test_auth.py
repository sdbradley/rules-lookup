import pytest
from fastapi import HTTPException

import auth


def test_verify_token_missing_header():
    with pytest.raises(HTTPException) as exc:
        auth.verify_token(None)
    assert exc.value.status_code == 401


def test_verify_token_bad_scheme():
    with pytest.raises(HTTPException) as exc:
        auth.verify_token("Basic sometoken")
    assert exc.value.status_code == 401


def test_verify_token_valid(mocker):
    mocker.patch(
        "auth.firebase_auth.verify_id_token",
        return_value={"uid": "user-123"},
    )
    uid = auth.verify_token("Bearer valid-token")
    assert uid == "user-123"
    auth.firebase_auth.verify_id_token.assert_called_once_with("valid-token")


def test_verify_token_invalid(mocker):
    mocker.patch(
        "auth.firebase_auth.verify_id_token",
        side_effect=Exception("token expired"),
    )
    with pytest.raises(HTTPException) as exc:
        auth.verify_token("Bearer bad-token")
    assert exc.value.status_code == 401
