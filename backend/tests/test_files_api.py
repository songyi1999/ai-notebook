import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.file import File
from backend.app.schemas.file import FileCreate

def test_create_file(client: TestClient):
    file_data = {
        "file_path": "notes/test/new_note.md",
        "title": "新笔记",
        "content": "这是一篇新创建的测试笔记。"
    }
    response = client.post("/api/v1/files", json=file_data)
    assert response.status_code == 201
    data = response.json()
    assert data["file_path"] == file_data["file_path"]
    assert data["title"] == file_data["title"]
    assert "id" in data

def test_read_file(client: TestClient, db_session: Session):
    # Create a file directly in DB for testing read
    new_file = File(
        file_path="notes/read_test.md",
        title="读取测试",
        content="这是用于读取测试的笔记。"
    )
    db_session.add(new_file)
    db_session.commit()
    db_session.refresh(new_file)

    response = client.get(f"/api/v1/files/{new_file.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == new_file.id
    assert data["title"] == new_file.title

def test_read_non_existent_file(client: TestClient):
    response = client.get("/api/v1/files/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": "File not found"}

def test_read_files(client: TestClient, db_session: Session):
    # Create multiple files
    file1 = File(file_path="notes/file1.md", title="文件1")
    file2 = File(file_path="notes/file2.md", title="文件2")
    db_session.add_all([file1, file2])
    db_session.commit()

    response = client.get("/api/v1/files")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2 # May contain files from other tests
    assert any(f["title"] == "文件1" for f in data)
    assert any(f["title"] == "文件2" for f in data)

def test_update_file(client: TestClient, db_session: Session):
    existing_file = File(
        file_path="notes/update_test.md",
        title="更新测试原标题",
        content="原始内容"
    )
    db_session.add(existing_file)
    db_session.commit()
    db_session.refresh(existing_file)

    update_data = {"title": "更新测试新标题", "content": "更新后的内容"}
    response = client.put(f"/api/v1/files/{existing_file.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == existing_file.id
    assert data["title"] == update_data["title"]
    assert data["content"] == update_data["content"]

def test_update_non_existent_file(client: TestClient):
    response = client.put("/api/v1/files/9999", json={
        "title": "不存在的文件"
    })
    assert response.status_code == 404
    assert response.json() == {"detail": "File not found"}

def test_delete_file(client: TestClient, db_session: Session):
    existing_file = File(
        file_path="notes/delete_test.md",
        title="删除测试",
        is_deleted=False
    )
    db_session.add(existing_file)
    db_session.commit()
    db_session.refresh(existing_file)

    response = client.delete(f"/api/v1/files/{existing_file.id}")
    assert response.status_code == 204

    # Verify it's soft deleted
    response = client.get(f"/api/v1/files/{existing_file.id}")
    assert response.status_code == 404 # Soft deleted means not found by default get

    # Verify it exists if include_deleted is True
    response = client.get("/api/v1/files", params={"include_deleted": True})
    assert response.status_code == 200
    data = response.json()
    assert any(f["id"] == existing_file.id and f["is_deleted"] == True for f in data)

def test_delete_non_existent_file(client: TestClient):
    response = client.delete("/api/v1/files/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": "File not found"} 