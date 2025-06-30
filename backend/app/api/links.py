from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..schemas.link import LinkCreate, LinkUpdate, LinkResponse
from ..services.link_service import LinkService
from ..database.session import get_db

router = APIRouter()

@router.post("/links", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
def create_link_api(link: LinkCreate, db: Session = Depends(get_db)):
    link_service = LinkService(db)
    db_link = link_service.create_link(link)
    return db_link

@router.get("/links/{link_id}", response_model=LinkResponse)
def read_link_api(link_id: int, db: Session = Depends(get_db)):
    link_service = LinkService(db)
    db_link = link_service.get_link(link_id)
    if db_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    return db_link

@router.get("/files/{file_id}/links", response_model=List[LinkResponse])
def read_links_by_file_api(file_id: int, db: Session = Depends(get_db)):
    link_service = LinkService(db)
    links = link_service.get_links_by_source_file(file_id)
    return links

@router.get("/links", response_model=List[LinkResponse])
def read_all_links_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    link_service = LinkService(db)
    links = link_service.get_all_links(skip=skip, limit=limit)
    return links

@router.put("/links/{link_id}", response_model=LinkResponse)
def update_link_api(link_id: int, link: LinkUpdate, db: Session = Depends(get_db)):
    link_service = LinkService(db)
    db_link = link_service.update_link(link_id=link_id, link_update=link)
    if db_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    return db_link

@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link_api(link_id: int, db: Session = Depends(get_db)):
    link_service = LinkService(db)
    db_link = link_service.delete_link(link_id=link_id)
    if db_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    return 