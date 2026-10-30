"""Tests for file upload, download and internal validation."""

from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import AsyncClient


async def _create_link(client: AsyncClient, file_id: str, user_id: str) -> str:
    resp = await client.post(f"/files/{file_id}/link", headers={"X-User-Id": user_id})
    return resp.json()["url"]


async def _upload(client: AsyncClient, user_id: str, content: bytes = b"hello world"):
    chat_id = str(uuid4())
    upload = await client.post(
        f"/files?chat_id={chat_id}",
        content=content,
        headers={
            "X-User-Id": user_id,
            "X-Filename": "hello.txt",
            "Content-Type": "text/plain",
        },
    )
    assert upload.status_code == 201
    return upload.json()


async def test_upload_and_download_roundtrip(client: AsyncClient):
    """An uploaded file's bytes come back unchanged on download."""
    user_id = str(uuid4())
    body = await _upload(client, user_id)
    assert body["status"] == "ready"
    assert body["size_bytes"] == len(b"hello world")

    download = await client.get(f"/files/{body['id']}", headers={"X-User-Id": user_id})
    assert download.status_code == 200
    assert download.content == b"hello world"


async def test_download_authorizes_via_message_access_not_chat_membership(
    client: AsyncClient, mock_communication_service
):
    """Download authorization goes through the message-based /access/ check.

    Not the chat-membership endpoint — required for a broadcast attachment
    to be downloadable by recipients who were never members of the chat it
    was originally uploaded into.
    """
    user_id = str(uuid4())
    body = await _upload(client, user_id)

    download = await client.get(f"/files/{body['id']}", headers={"X-User-Id": user_id})
    assert download.status_code == 200

    called_urls = [
        call.args[0]
        for call in mock_communication_service.return_value.get.call_args_list
    ]
    assert any("/access/" in url for url in called_urls)


async def test_download_is_forbidden_when_access_check_denies(
    client: AsyncClient, mock_communication_service
):
    """A user with no message-level access to the file is rejected."""

    def _deny_access_allow_membership(url, *args, **kwargs):
        response = AsyncMock()
        response.raise_for_status = lambda: None
        if url.endswith("/members"):
            response.json = lambda: {"user_ids": []}
        elif "/access/" in url:
            response.json = lambda: {"authorized": False}
        else:
            response.json = lambda: {"is_member": True}
        return response

    mock_communication_service.return_value.get.side_effect = (
        _deny_access_allow_membership
    )

    user_id = str(uuid4())
    body = await _upload(client, user_id)

    download = await client.get(f"/files/{body['id']}", headers={"X-User-Id": user_id})

    assert download.status_code == 403


async def test_download_without_range_reports_whole_size(client: AsyncClient):
    """No Range header -> 200, Accept-Ranges, and Content-Length = file size."""
    user_id = str(uuid4())
    body = await _upload(client, user_id)

    download = await client.get(f"/files/{body['id']}", headers={"X-User-Id": user_id})

    assert download.status_code == 200
    assert download.headers["accept-ranges"] == "bytes"
    assert download.headers["content-length"] == str(len(b"hello world"))


async def test_download_with_range_returns_206_partial_content(client: AsyncClient):
    """A satisfiable Range request returns 206 with just the requested bytes."""
    user_id = str(uuid4())
    body = await _upload(client, user_id, content=b"0123456789")

    download = await client.get(
        f"/files/{body['id']}",
        headers={"X-User-Id": user_id, "Range": "bytes=0-3"},
    )

    assert download.status_code == 206
    assert download.headers["content-range"] == "bytes 0-3/10"
    assert download.headers["content-length"] == "4"
    assert download.content == b"0123"


async def test_download_with_open_ended_range_goes_to_end_of_file(
    client: AsyncClient,
):
    """"bytes=N-" (no end) returns everything from N to the last byte."""
    user_id = str(uuid4())
    body = await _upload(client, user_id, content=b"0123456789")

    download = await client.get(
        f"/files/{body['id']}",
        headers={"X-User-Id": user_id, "Range": "bytes=7-"},
    )

    assert download.status_code == 206
    assert download.headers["content-range"] == "bytes 7-9/10"
    assert download.content == b"789"


async def test_download_with_out_of_bounds_range_is_416(client: AsyncClient):
    """A range past the end of the file is rejected, not silently clamped."""
    user_id = str(uuid4())
    body = await _upload(client, user_id, content=b"0123456789")

    download = await client.get(
        f"/files/{body['id']}",
        headers={"X-User-Id": user_id, "Range": "bytes=9999-10000"},
    )

    assert download.status_code == 416
    assert download.headers["content-range"] == "bytes */10"


async def test_download_missing_file_is_404(client: AsyncClient):
    """A download for an unknown file id returns 404."""
    resp = await client.get(
        f"/files/{uuid4()}", headers={"X-User-Id": str(uuid4())}
    )
    assert resp.status_code == 404


async def test_download_without_any_credentials_is_401(client: AsyncClient):
    """Neither X-User-Id nor a signed link means no authorization at all."""
    user_id = str(uuid4())
    body = await _upload(client, user_id)

    resp = await client.get(f"/files/{body['id']}")

    assert resp.status_code == 401


async def test_create_link_returns_a_usable_signed_url(client: AsyncClient):
    """Issuing a link runs the same authorization as a direct download."""
    user_id = str(uuid4())
    body = await _upload(client, user_id)

    resp = await client.post(
        f"/files/{body['id']}/link", headers={"X-User-Id": user_id}
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["expires_in"] == 300
    assert f"/files/{body['id']}?sig=" in payload["url"]
    assert "&exp=" in payload["url"]


async def test_download_via_a_freshly_issued_signed_link_needs_no_user_id(
    client: AsyncClient,
):
    """The whole point: sig+exp alone is enough, no X-User-Id at all."""
    user_id = str(uuid4())
    body = await _upload(client, user_id)
    url = await _create_link(client, body["id"], user_id)
    sig_and_exp = url.split("?", 1)[1]

    download = await client.get(f"/files/{body['id']}?{sig_and_exp}")

    assert download.status_code == 200
    assert download.content == b"hello world"


async def test_download_with_a_tampered_signature_is_403(client: AsyncClient):
    """A signature that doesn't match its (file_id, exp) pair is rejected."""
    user_id = str(uuid4())
    body = await _upload(client, user_id)
    url = await _create_link(client, body["id"], user_id)
    exp = url.split("exp=")[1]

    resp = await client.get(f"/files/{body['id']}?sig=0000&exp={exp}")

    assert resp.status_code == 403


async def test_download_with_an_expired_link_is_403(client: AsyncClient):
    """A link whose exp has already passed is rejected, signature notwithstanding."""
    user_id = str(uuid4())
    body = await _upload(client, user_id)

    resp = await client.get(f"/files/{body['id']}?sig=anything&exp=1")

    assert resp.status_code == 403


async def test_internal_validate_only_returns_ready_files_in_chat(client: AsyncClient):
    """validate_files only accepts files that are ready and belong to the chat."""
    chat_id = str(uuid4())
    other_chat_id = str(uuid4())
    user_id = str(uuid4())

    upload = await client.post(
        f"/files?chat_id={chat_id}",
        content=b"data",
        headers={"X-User-Id": user_id, "X-Filename": "f.bin"},
    )
    file_id = upload.json()["id"]

    resp = await client.post(
        "/internal/files/validate",
        json={"chat_id": chat_id, "file_ids": [file_id, str(uuid4())]},
    )
    assert resp.json()["valid_file_ids"] == [file_id]

    resp_wrong_chat = await client.post(
        "/internal/files/validate",
        json={"chat_id": other_chat_id, "file_ids": [file_id]},
    )
    assert resp_wrong_chat.json()["valid_file_ids"] == []
