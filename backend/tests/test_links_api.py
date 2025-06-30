import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.file import File
from backend.app.models.link import Link
from backend.app.schemas.link import LinkCreate

def test_create_link(client: TestClient, db_session: Session):
    # Create a source file
    source_file = File(file_path="notes/test/source_note.md", title="源笔记")
    db_session.add(source_file)
    db_session.commit()
    db_session.refresh(source_file)

    link_data = {
        "source_file_id": source_file.id,
        "link_text": "[[目标文件]]",
        "link_type": "wikilink"
    }
    response = client.post("/api/v1/links", json=link_data)
    assert response.status_code == 201
    data = response.json()
    assert data["source_file_id"] == link_data["source_file_id"]
    assert data["link_text"] == link_data["link_text"]
    assert "id" in data

def test_read_link(client: TestClient, db_session: Session):
    source_file = File(file_path="notes/read_source.md", title="读取源")
    target_file = File(file_path="notes/read_target.md", title="读取目标")
    db_session.add_all([source_file, target_file])
    db_session.commit()
    db_session.refresh(source_file)
    db_session.refresh(target_file)

    new_link = Link(
        source_file_id=source_file.id,
        target_file_id=target_file.id,
        link_text="[[测试读取链接]]"
    )
    db_session.add(new_link)
    db_session.commit()
    db_session.refresh(new_link)

    response = client.get(f"/api/v1/links/{new_link.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == new_link.id
    assert data["link_text"] == new_link.link_text

def test_read_non_existent_link(client: TestClient):
    response = client.get("/api/v1/links/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Link not found"}

def test_read_links_by_file(client: TestClient, db_session: Session):
    source_file = File(file_path="notes/file_link_source.md", title="文件链接源")
    target_file1 = File(file_path="notes/file_link_target1.md", title="文件链接目标1")
    target_file2 = File(file_path="notes/file_link_target2.md", title="文件链接目标2")
    db_session.add_all([source_file, target_file1, target_file2])
    db_session.commit()
    db_session.refresh(source_file)
    db_session.refresh(target_file1)
    db_session.refresh(target_file2)

    link1 = Link(source_file_id=source_file.id, target_file_id=target_file1.id, link_text="[[目标1]]")
    link2 = Link(source_file_id=source_file.id, target_file_id=target_file2.id, link_text="[[目标2]]")
    db_session.add_all([link1, link2])
    db_session.commit()

    response = client.get(f"/api/v1/files/{source_file.id}/links")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(l["link_text"] == "[[目标1]]" for l in data)
    assert any(l["link_text"] == "[[目标2]]" for l in data)

def test_update_link(client: TestClient, db_session: Session):
    source_file = File(file_path="notes/update_link_source.md", title="更新链接源")
    target_file = File(file_path="notes/update_link_target.md", title="更新链接目标")
    db_session.add_all([source_file, target_file])
    db_session.commit()
    db_session.refresh(source_file)
    db_session.refresh(target_file)

    existing_link = Link(
        source_file_id=source_file.id,
        target_file_id=target_file.id,
        link_text="[[旧链接]]"
    )
    db_session.add(existing_link)
    db_session.commit()
    db_session.refresh(existing_link)

    update_data = {"link_text": "[[新链接]]", "is_valid": False}
    response = client.put(f"/api/v1/links/{existing_link.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == existing_link.id
    assert data["link_text"] == update_data["link_text"]
    assert data["is_valid"] == update_data["is_valid"]

def test_update_non_existent_link(client: TestClient):
    response = client.put("/api/v1/links/9999", json={
        "link_text": "[[不存在的链接]]"
    })
    assert response.status_code == 404
    assert response.json() == {"detail": "Link not found"}

def test_delete_link(client: TestClient, db_session: Session):
    source_file = File(file_path="notes/delete_link_source.md", title="删除链接源")
    target_file = File(file_path="notes/delete_link_target.md", title="删除链接目标")
    db_session.add_all([source_file, target_file])
    db_session.commit()
    db_session.refresh(source_file)
    db_session.refresh(target_file)

    existing_link = Link(
        source_file_id=source_file.id,
        target_file_id=target_file.id,
        link_text="[[要删除的链接]]"
    )
    db_session.add(existing_link)
    db_session.commit()
    db_session.refresh(existing_link)

    response = client.delete(f"/api/v1/links/{existing_link.id}")
    assert response.status_code == 204

    # Verify it's deleted
    response = client.get(f"/api/v1/links/{existing_link.id}")
    assert response.status_code == 404 