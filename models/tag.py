import datetime
import uuid
import enum
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, Enum, ForeignKey, func, Table, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import Index
from core.database import Base

task_tags = Table('task_tags', Base.metadata, Column('task_id', UUID(as_uuid=True),ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True),
                  Column('tag_id', UUID(as_uuid=True),ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
                  Column('attached_at', DateTime(timezone=True), nullable = False, server_default=func.now(), index=True))


class Tag(Base):
    __tablename__ = "tags"
    id = Column(UUID(as_uuid=True), primary_key=True, default = uuid.uuid4, index=True)
    name = Column(String(50), unique=True, nullable = False, index = True)
    color = Column(String(7), nullable = False)
    created_at = Column(DateTime(timezone=True), nullable= False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name='check_color_hex'),
    )

    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}', color='{self.color}')>"
    task = relationship("Task", back_populates="tag")
