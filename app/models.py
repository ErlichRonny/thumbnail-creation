import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum as SAEnum, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.constants import ImageStatus


class Base(DeclarativeBase):
    pass


class Image(Base):
    __tablename__ = "images"
    __table_args__ = (Index("ix_images_status_created_at", "status", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[ImageStatus] = mapped_column(
        SAEnum(ImageStatus, name="image_status"), nullable=False, default=ImageStatus.PENDING
    )
    original_file_name: Mapped[str] = mapped_column(String, nullable=False)
    original_storage_path: Mapped[str] = mapped_column(String, nullable=False)
    thumbnail_storage_path: Mapped[str | None] = mapped_column(String, nullable=True)
    preset: Mapped[str | None] = mapped_column(String, nullable=True)
    custom_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    custom_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_width: Mapped[int] = mapped_column(Integer, nullable=False)
    original_height: Mapped[int] = mapped_column(Integer, nullable=False)
    thumbnail_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
