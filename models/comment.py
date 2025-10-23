import uuid
from sqlalchemy import Column, String,DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import Index
from core.database import Base


class Comment(Base):
    __tablename__ = "comments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey ("tasks.id",ondelete="CASCADE"), nullable=False, index = True)
    user_id = Column (UUID(as_uuid=True), ForeignKey ("users.id",ondelete="CASCADE"), nullable=False, index = True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True),  server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)


    task = relationship("Task", foreign_keys=[task_id], back_populates="comments")
    author = relationship("User", foreign_keys=[user_id], back_populates="comments")

    __table_args__ = (
        Index('ix_comments_task_created', 'task_id', 'created_at'),
    )

    def __repr__(self):
        return f"<Comment(id={self.id}, task_id={self.task_id}, by={self.user_id})>"
