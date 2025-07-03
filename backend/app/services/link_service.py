from sqlalchemy.orm import Session
from typing import List, Optional

from ..models.link import Link
from ..models.file import File
from ..schemas.link import LinkCreate, LinkUpdate

class LinkService:
    def __init__(self, db: Session):
        self.db = db

    def create_link(self, link: LinkCreate) -> Link:
        # 如果没有提供link_text，自动生成一个
        link_data = link.dict()
        if not link_data.get('link_text'):
            # 尝试获取目标文件的标题作为link_text
            if link_data.get('target_file_id'):
                target_file = self.db.query(File).filter(File.id == link_data['target_file_id']).first()
                if target_file:
                    link_data['link_text'] = f"[[{target_file.title or target_file.file_path.split('/')[-1]}]]"
                else:
                    link_data['link_text'] = f"链接到文件ID: {link_data['target_file_id']}"
            else:
                # 如果没有目标文件ID，使用链接类型作为默认文本
                link_data['link_text'] = f"{link_data.get('link_type', 'unknown')} 链接"
        
        db_link = Link(**link_data)
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