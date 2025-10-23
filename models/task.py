import uuid
import enum
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import Index
from core.database import Base
from models.tag import task_tags


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"

class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(Base):
    __tablename__ = "tasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(150), nullable=False, index = True)
    description = Column(String(400))
    status = Column(Enum(TaskStatus, name = "task_status"), nullable = False, default=TaskStatus.TODO, index = True)
    priority = Column(Enum(TaskPriority, name="task_priority"), nullable=False, default=TaskPriority.MEDIUM, index = True)
    due_date = Column (DateTime(timezone=True), nullable = True, index = True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable = False)
    assigned_to =Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable = True)
    created_at = Column(DateTime(timezone=True), nullable= False, server_default= func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)


    creator = relationship("User", foreign_keys=[created_by], back_populates= "task_created")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates= "task_assigned" )
    comment = relationship("comment", back_populates="task", cascade="all, delete_orphan")
    tags = relationship('Tag', secondary=task_tags, back_populates='tasks')
    __table_args__ = (
        Index('ix_tasks_created_by_status', 'created_by', 'status'),
        Index('ix_tasks_assigned_to_status', 'assigned_to', 'status'),
        Index('ix_tasks_status_due_date', 'status', 'due_date'),
        Index('ix_tasks_deleted_at', 'deleted_at'),
    )


    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', status={self.status.value})>"





