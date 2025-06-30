import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.tag import Tag
from backend.app.models.file import File
from backend.app.models.file_tag import FileTag
from backend.app.schemas.tag import TagCreate, FileTagCreate

def test_create_tag(client: TestClient):
    tag_data = {
        "name": "pytest_tag",
        "color": "#FF0000",
        "description": "一个用于测试的标签"
    }
    response = client.post("/api/v1/tags", json=tag_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == tag_data["name"]
    assert "id" in data

def test_read_tag(client: TestClient, db_session: Session):
    new_tag = Tag(name="read_test_tag", color="#00FF00")
    db_session.add(new_tag)
    db_session.commit()
    db_session.refresh(new_tag)

    response = client.get(f"/api/v1/tags/{new_tag.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == new_tag.id
    assert data["name"] == new_tag.name

def test_read_non_existent_tag(client: TestClient):
    response = client.get("/api/v1/tags/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Tag not found"}

def test_read_all_tags(client: TestClient, db_session: Session):
    tag1 = Tag(name="tag1")
    tag2 = Tag(name="tag2")
    db_session.add_all([tag1, tag2])
    db_session.commit()

    response = client.get("/api/v1/tags")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(t["name"] == "tag1" for t in data)
    assert any(t["name"] == "tag2" for t in data)

def test_update_tag(client: TestClient, db_session: Session):
    existing_tag = Tag(name="old_tag_name", description="旧描述")
    db_session.add(existing_tag)
    db_session.commit()
    db_session.refresh(existing_tag)

    update_data = {"name": "new_tag_name", "color": "#0000FF"}
    response = client.put(f"/api/v1/tags/{existing_tag.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == existing_tag.id
    assert data["name"] == update_data["name"]
    assert data["color"] == update_data["color"]

def test_update_non_existent_tag(client: TestClient):
    response = client.put("/api/v1/tags/9999", json={
        "name": "non_existent"
    })
    assert response.status_code == 404
    assert response.json() == {"detail": "Tag not found"}

def test_delete_tag(client: TestClient, db_session: Session):
    existing_tag = Tag(name="tag_to_delete")
    db_session.add(existing_tag)
    db_session.commit()
    db_session.refresh(existing_tag)

    response = client.delete(f"/api/v1/tags/{existing_tag.id}")
    assert response.status_code == 204

    response = client.get(f"/api/v1/tags/{existing_tag.id}")
    assert response.status_code == 404

# FileTag API Tests

def test_create_file_tag(client: TestClient, db_session: Session):
    file = File(file_path="notes/file_for_filetag.md", title="文件用于文件标签")
    tag = Tag(name="tag_for_filetag")
    db_session.add_all([file, tag])
    db_session.commit()
    db_session.refresh(file)
    db_session.refresh(tag)

    file_tag_data = {
        "file_id": file.id,
        "tag_id": tag.id,
        "relevance_score": 0.8
    }
    response = client.post("/api/v1/file_tags", json=file_tag_data)
    assert response.status_code == 201
    data = response.json()
    assert data["file_id"] == file.id
    assert data["tag_id"] == tag.id

def test_get_file_tags(client: TestClient, db_session: Session):
    file = File(file_path="notes/file_for_get_file_tags.md", title="获取文件标签的文件")
    tag1 = Tag(name="get_tag1")
    tag2 = Tag(name="get_tag2")
    db_session.add_all([file, tag1, tag2])
    db_session.commit()
    db_session.refresh(file)
    db_session.refresh(tag1)
    db_session.refresh(tag2)

    file_tag1 = FileTag(file_id=file.id, tag_id=tag1.id)
    file_tag2 = FileTag(file_id=file.id, tag_id=tag2.id)
    db_session.add_all([file_tag1, file_tag2])
    db_session.commit()

    response = client.get(f"/api/v1/files/{file.id}/tags")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(ft["tag_id"] == tag1.id for ft in data)
    assert any(ft["tag_id"] == tag2.id for ft in data)

def test_delete_file_tag(client: TestClient, db_session: Session):
    file = File(file_path="notes/file_for_delete_file_tag.md", title="删除文件标签的文件")
    tag = Tag(name="delete_tag")
    db_session.add_all([file, tag])
    db_session.commit()
    db_session.refresh(file)
    db_session.refresh(tag)

    file_tag = FileTag(file_id=file.id, tag_id=tag.id)
    db_session.add(file_tag)
    db_session.commit()

    response = client.delete(f"/api/v1/files/{file.id}/tags/{tag.id}")
    assert response.status_code == 204

    # Verify it's deleted
    response = client.get(f"/api/v1/files/{file.id}/tags")
    assert response.status_code == 200
    data = response.json()
    assert not any(ft["tag_id"] == tag.id for ft in data) 