"""人格库 / 策略库 API 模型"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class LibraryListItem(BaseModel):
    id: str
    name: str
    is_builtin: bool = False
    personality_count: Optional[int] = None
    strategy_role_count: Optional[int] = None
    updated_at: Optional[str] = None


class PersonalityLibrary(BaseModel):
    id: str
    name: str
    is_builtin: bool = False
    personalities: list[dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CreatePersonalityLibraryRequest(BaseModel):
    name: str
    personalities: list[dict[str, Any]] = Field(default_factory=list)
    fork_from: Optional[str] = None


class UpdatePersonalityLibraryRequest(BaseModel):
    name: Optional[str] = None
    personalities: Optional[list[dict[str, Any]]] = None


class StrategyLibrary(BaseModel):
    id: str
    name: str
    is_builtin: bool = False
    strategies_by_role: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CreateStrategyLibraryRequest(BaseModel):
    name: str
    strategies_by_role: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    fork_from: Optional[str] = None


class UpdateStrategyLibraryRequest(BaseModel):
    name: Optional[str] = None
    strategies_by_role: Optional[dict[str, list[dict[str, Any]]]] = None


class PatchStrategyLibraryRequest(BaseModel):
    """延续：向库中追加策略条目"""
    name: Optional[str] = None
    append_by_role: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
