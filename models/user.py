import enum
import uuid

from sqlalchemy import String, Column, Float, Integer, Boolean, DateTime, Enum, func
from sqlalchemy.orm import relationship
from core.database import Base
from sqlalchemy.dialects.postgresql import UUID

class Roles(str, enum.Enum):
    ADMIN = "admin"
    MEMBER ="member"

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(100), nullable = False, index=True, unique=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(Roles,name ="user_roles"), nullable=False, default=Roles.MEMBER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default= func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


    task_created = relationship("Task", foreign_keys= "Task.created_by", back_populates="creator")
    task_assigned = relationship("Task", foreign_keys= "Task.assigned_to", back_populates="assignee")




