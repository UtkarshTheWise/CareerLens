from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.catalogue import validate_catalogue
from app.config import API_VERSION, check_settings, get_settings
from app.db.base import SessionLocal, create_all
from app.errors import register_error_handlers
from app.routers import analyses, applications, cohorts, jobs, meta, profiles, quizzes
from app.services.pipeline import recover_interrupted


@asynccontextmanager
async def lifespan(_: FastAPI):
    check_settings(get_settings())  # refuse an unsafe production configuration
    validate_catalogue()  # refuse to start on broken data/*.yaml
    create_all()  # prototype: no migrations yet
    with SessionLocal() as db:
        recover_interrupted(db)  # a restart can't resume a half-done analysis
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
    app.include_router(analyses.router)
    app.include_router(jobs.router)
    app.include_router(applications.router)
    app.include_router(cohorts.router)
    app.include_router(quizzes.router)
    return app


app = create_app()
