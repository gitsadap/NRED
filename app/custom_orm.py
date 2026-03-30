from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import TypeVar, Type, List, Optional, Any, Dict
from sqlalchemy.inspection import inspect
from app.database import Base

T = TypeVar("T", bound="ModelBase")

class ModelBase(Base):
    __abstract__ = True

    @classmethod
    def _get_pk_name(cls):
        return inspect(cls).primary_key[0].name

    @classmethod
    async def get_by_id(cls: Type[T], session: AsyncSession, id: Any) -> Optional[T]:
        pk_name = cls._get_pk_name()
        result = await session.execute(select(cls).where(getattr(cls, pk_name) == id))
        return result.scalars().first()

    @classmethod
    async def get_all(cls: Type[T], session: AsyncSession) -> List[T]:
        result = await session.execute(select(cls))
        return result.scalars().all()

    @classmethod
    async def filter(cls: Type[T], session: AsyncSession, **kwargs) -> List[T]:
        query = select(cls)
        for key, value in kwargs.items():
            query = query.where(getattr(cls, key) == value)
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def first(cls: Type[T], session: AsyncSession, **kwargs) -> Optional[T]:
        query = select(cls)
        for key, value in kwargs.items():
            query = query.where(getattr(cls, key) == value)
        result = await session.execute(query)
        return result.scalars().first()

    @classmethod
    def create(cls: Type[T], session: AsyncSession, **kwargs) -> T:
        instance = cls(**kwargs)
        session.add(instance)
        return instance

    @classmethod
    async def update(cls: Type[T], session: AsyncSession, id: Any, **kwargs) -> Optional[T]:
        pk_name = cls._get_pk_name()
        query = update(cls).where(getattr(cls, pk_name) == id).values(**kwargs)
        await session.execute(query)
        return await cls.get_by_id(session, id)

    @classmethod
    async def delete_by_id(cls: Type[T], session: AsyncSession, id: Any) -> bool:
        pk_name = cls._get_pk_name()
        query = delete(cls).where(getattr(cls, pk_name) == id)
        result = await session.execute(query)
        return result.rowcount > 0
