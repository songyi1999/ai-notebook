from sqlalchemy.orm import Session
from typing import List, Optional

from ..models.link import Link
from ..models.file import File
from ..schemas.link import LinkCreate, LinkUpdate

class LinkService:
    def __init__(self, db: Session):
        self.db = db

    def create_link(self, link: LinkCreate) -> Link:
        db_link = Link(**link.dict())
        self.db.add(db_link)
        self.db.commit()
        self.db.refresh(db_link)
        return db_link

    def get_link(self, link_id: int) -> Optional[Link]:
        return self.db.query(Link).filter(Link.id == link_id).first()

    def get_links_by_source_file(self, source_file_id: int) -> List[Link]:
        return self.db.query(Link).filter(Link.source_file_id == source_file_id).all()

    def get_links_by_target_file(self, target_file_id: int) -> List[Link]:
        return self.db.query(Link).filter(Link.target_file_id == target_file_id).all()

    def get_all_links(self, skip: int = 0, limit: int = 100) -> List[Link]:
        return self.db.query(Link).offset(skip).limit(limit).all()

    def update_link(self, link_id: int, link_update: LinkUpdate) -> Optional[Link]:
        db_link = self.get_link(link_id)
        if not db_link:
            return None
        for key, value in link_update.dict(exclude_unset=True).items():
            setattr(db_link, key, value)
        self.db.commit()
        self.db.refresh(db_link)
        return db_link

    def delete_link(self, link_id: int) -> Optional[Link]:
        db_link = self.get_link(link_id)
        if not db_link:
            return None
        self.db.delete(db_link)
        self.db.commit()
        return db_link 