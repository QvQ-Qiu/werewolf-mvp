"""人格库 / 策略库 REST API"""

from fastapi import APIRouter, Response

from app.models.libraries import (
    CreatePersonalityLibraryRequest,
    CreateStrategyLibraryRequest,
    LibraryListItem,
    PatchStrategyLibraryRequest,
    PersonalityLibrary,
    StrategyLibrary,
    UpdatePersonalityLibraryRequest,
    UpdateStrategyLibraryRequest,
)
from app.services import library_store

router = APIRouter(prefix="/libraries", tags=["libraries"])


@router.get("/personalities", response_model=list[LibraryListItem])
async def list_personality_libraries() -> list[LibraryListItem]:
    return [LibraryListItem(**x) for x in library_store.list_personality_libraries()]


@router.post("/personalities", response_model=PersonalityLibrary, status_code=201)
async def create_personality_library(body: CreatePersonalityLibraryRequest) -> PersonalityLibrary:
    data = library_store.create_personality_library(
        body.name,
        personalities=body.personalities,
        fork_from=body.fork_from,
    )
    return PersonalityLibrary(**data)


@router.get("/personalities/{library_id}", response_model=PersonalityLibrary)
async def get_personality_library(library_id: str) -> PersonalityLibrary:
    return PersonalityLibrary(**library_store.get_personality_library(library_id))


@router.put("/personalities/{library_id}", response_model=PersonalityLibrary)
async def update_personality_library(
    library_id: str, body: UpdatePersonalityLibraryRequest
) -> PersonalityLibrary:
    data = library_store.update_personality_library(
        library_id,
        name=body.name,
        personalities=body.personalities,
    )
    return PersonalityLibrary(**data)


@router.delete("/personalities/{library_id}", status_code=204)
async def delete_personality_library(library_id: str) -> Response:
    library_store.delete_personality_library(library_id)
    return Response(status_code=204)


@router.get("/strategies", response_model=list[LibraryListItem])
async def list_strategy_libraries() -> list[LibraryListItem]:
    return [LibraryListItem(**x) for x in library_store.list_strategy_libraries()]


@router.post("/strategies", response_model=StrategyLibrary, status_code=201)
async def create_strategy_library(body: CreateStrategyLibraryRequest) -> StrategyLibrary:
    data = library_store.create_strategy_library(
        body.name,
        strategies_by_role=body.strategies_by_role,
        fork_from=body.fork_from,
    )
    library_store.clear_strategy_cache()
    return StrategyLibrary(**data)


@router.get("/strategies/{library_id}", response_model=StrategyLibrary)
async def get_strategy_library(library_id: str) -> StrategyLibrary:
    return StrategyLibrary(**library_store.get_strategy_library(library_id))


@router.put("/strategies/{library_id}", response_model=StrategyLibrary)
async def update_strategy_library(
    library_id: str, body: UpdateStrategyLibraryRequest
) -> StrategyLibrary:
    data = library_store.update_strategy_library(
        library_id,
        name=body.name,
        strategies_by_role=body.strategies_by_role,
    )
    library_store.clear_strategy_cache()
    return StrategyLibrary(**data)


@router.patch("/strategies/{library_id}", response_model=StrategyLibrary)
async def patch_strategy_library(
    library_id: str, body: PatchStrategyLibraryRequest
) -> StrategyLibrary:
    """延续：向已有策略库追加条目"""
    data = library_store.patch_strategy_library_extend(
        library_id,
        body.append_by_role,
        name=body.name,
    )
    library_store.clear_strategy_cache()
    return StrategyLibrary(**data)


@router.delete("/strategies/{library_id}", status_code=204)
async def delete_strategy_library(library_id: str) -> Response:
    library_store.delete_strategy_library(library_id)
    library_store.clear_strategy_cache()
    return Response(status_code=204)
