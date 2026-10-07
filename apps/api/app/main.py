from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.catalogue import validate_catalogue
from app.config import API_VERSION, get_settings
from app.db.base import create_all
from app.errors import register_error_handlers
from app.routers import meta, profiles


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_catalogue()  # refuse to start on broken data/*.yaml
    create_all()  # prototype: no migrations yet
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CareerLens API",
        version=API_VERSION,
        lifespan=lifespan,
        # One schema per model, named as in the contract (no -Input/-Output variants).
        separate_input_output_schemas=False,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=r"chrome-extension://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(meta.router)
    app.include_router(profiles.router)
    return app


app = create_app()
