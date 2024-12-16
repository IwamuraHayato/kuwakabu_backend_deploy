from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
 

class Base(DeclarativeBase):
    pass

class Posts(Base):
    __tablename__ = 'posts'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    collected_at: Mapped[datetime] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    deleted_at: Mapped[datetime] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class Images(Base):
    __tablename__ = 'images'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey('posts.id'), nullable=False)
    image_url: Mapped[str] = mapped_column()
    position: Mapped[int] = mapped_column(nullable=True)


class Location(Base):
    __tablename__ = 'location'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=True)
    prefecture: Mapped[str] = mapped_column(nullable=True)
    city: Mapped[str] = mapped_column(nullable=True)
    latitude: Mapped[float] = mapped_column(nullable=True)
    longitude: Mapped[float] = mapped_column(nullable=True)
    post_id: Mapped[int] = mapped_column(ForeignKey('posts.id'))


class Environment(Base):
    __tablename__ = 'environment'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey('posts.id'), nullable=False)
    whether: Mapped[str] = mapped_column(nullable=True)
    temperature: Mapped[float] = mapped_column(nullable=True)
    is_restricted_area: Mapped[bool] = mapped_column(nullable=True)
    crowd_level: Mapped[int] = mapped_column(nullable=True)
    free_memo: Mapped[str] = mapped_column(nullable=True)


class SpeciesInfo(Base):
    __tablename__ = 'species_info'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey('posts.id'), nullable=False)
    species_id: Mapped[int] = mapped_column(ForeignKey('species.id'), nullable=True)
    species_other: Mapped[str] = mapped_column(nullable=True)
    gender: Mapped[str] = mapped_column(nullable=True)
    count: Mapped[int] = mapped_column(nullable=True)
    max_size: Mapped[float] = mapped_column(nullable=True)


class Species(Base):
    __tablename__ = 'species'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)


class Method(Base):
    __tablename__ = 'method'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)


class Tree(Base):
    __tablename__ = 'tree'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)


class DangerousSpecies(Base):
    __tablename__ = 'dangerous_species'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)


class Facility(Base):
    __tablename__ = 'facility'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)


class MethodInfo(Base):
    __tablename__ = 'method_info'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey('posts.id'), nullable=False)
    method_id: Mapped[int] = mapped_column(ForeignKey('method.id'), nullable=True)
    method_other: Mapped[str] = mapped_column(nullable=True)


class TreeInfo(Base):
    __tablename__ = 'tree_info'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey('posts.id'), nullable=False)
    tree_id: Mapped[int] = mapped_column(ForeignKey('tree.id'), nullable=True)
    tree_other: Mapped[str] = mapped_column(nullable=True)


class DangerousSpeciesInfo(Base):
    __tablename__ = 'dangerous_species_info'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey('posts.id'), nullable=False)
    dangerous_species_id: Mapped[int] = mapped_column(ForeignKey('dangerous_species.id'), nullable=True)
    dangerous_species_other: Mapped[str] = mapped_column(nullable=True)


class FacilityInfo(Base):
    __tablename__ = 'facility_info'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey('posts.id'), nullable=False)
    facility_id: Mapped[int] = mapped_column(ForeignKey('facility.id'), nullable=True)
    facility_other: Mapped[str] = mapped_column(nullable=True)


class Users(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    icon: Mapped[str] = mapped_column(nullable=True)

    collection_start_at: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[str] = mapped_column(default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), nullable=False)
    updated_at: Mapped[str] = mapped_column(default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), nullable=True)
    password: Mapped[str] = mapped_column(nullable=True)


__all__ = [
    "Posts",
    "Images",
    "Location",
    "Environment",
    "SpeciesInfo",
    "Species",
    "Method",
    "Tree",
    "DangerousSpecies",
    "Facility",
    "MethodInfo",
    "TreeInfo",
    "DangerousSpeciesInfo",
    "FacilityInfo",
    "Users"
    ]


