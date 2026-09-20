"""Tests for file upload, download and internal validation."""

from uuid import uuid4

from httpx import AsyncClient


async def test_upload_and_download_roundtrip(client: AsyncClient):
    """An uploaded file's bytes come back unchanged on download."""
    chat_id = str(uuid4())
    user_id = str(uuid4())

    upload = await client.post(
        f"/files?chat_id={chat_id}",
        content=b"hello world",
        headers={
            "X-User-Id": user_id,
            "X-Filename": "hello.txt",
            "Content-Type": "text/plain",
        },
    )
    assert upload.status_code == 201
    body = upload.json()
    assert body["status"] == "ready"
    assert body["size_bytes"] == len(b"hello world")

    download = await client.get(f"/files/{body['id']}", headers={"X-User-Id": user_id})
    assert download.status_code == 200
    assert download.content == b"hello world"


async def test_download_missing_file_is_404(client: AsyncClient):
    """A download for an unknown file id returns 404."""
    resp = await client.get(
        f"/files/{uuid4()}", headers={"X-User-Id": str(uuid4())}
    )
    assert resp.status_code == 404


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
