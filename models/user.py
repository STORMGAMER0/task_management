import enum
import uuid

from sqlalchemy import String, Column, Float, Integer, Boolean, DateTime, Enum, func, Index
from sqlalchemy.orm import relationship
from core.database import Base
from sqlalchemy.dialects.postgresql import UUID

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER ="member"

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(100), nullable = False, index=True, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole,name ="user_roles"), nullable=False, default=UserRole.MEMBER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default= func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


    task_created = relationship("Task", foreign_keys= "Task.created_by", back_populates="creator", cascade="all, delete-orphan")
    task_assigned = relationship("Task", foreign_keys= "Task.assigned_to", back_populates="assignee")
    comments = relationship("Comment", back_populates = "author")

    __table_args__ = (
        Index('ix_users_email_active', 'email', 'is_active'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

