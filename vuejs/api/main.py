from fastapi import FastAPI, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import ResponseValidationError
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

import crud
from Routes import Jobs, Logs, Settings, Auth, Various
from Routes.Auth import get_current_active_user
from fastapi.middleware.cors import CORSMiddleware
from database import init_db

tags_metadata = [
    {"name": "Job Methods", "description": "Any methods that interact with the Jobs"},
    {"name": "Settings Methods", "description": "Settings methods for viewing/saving Settings in ARM"},
    {"name": "Log Methods", "description": "Log file methods"},
    {"name": "Auth Methods", "description": "Authorize sections"},
    {"name": "Various Methods", "description": "All other methods are stored here"},
]
app = FastAPI(openapi_tags=tags_metadata)


@app.exception_handler(ResponseValidationError)
async def validation_exception_handler(request: Request, exc: ResponseValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors()}),
    )


# Not safe - testing only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# app.include_router(Jobs.router,tags=["Job Methods"], dependencies=[Depends(get_current_active_user)])
# app.include_router(Logs.router, tags=['Log Methods'], dependencies=[Depends(get_current_active_user)])
# app.include_router(Settings.router,tags=["Settings Methods"], dependencies=[Depends(get_current_active_user)])
# app.include_router(Auth.router,tags=["Auth Methods"])
# app.include_router(Various.router,tags=["Various Methods"], dependencies=[Depends(get_current_active_user)])
# Not safe - testing only
app.include_router(Jobs.router, tags=["Job Methods"])
app.include_router(Logs.router, tags=['Log Methods'])
app.include_router(Settings.router, tags=["Settings Methods"])
app.include_router(Auth.router, tags=["Auth Methods"])
app.include_router(Various.router, tags=["Various Methods"])


# Create db tables if needed
@app.on_event("startup")
async def on_startup():
    await init_db()


@app.get("/")
async def api_health_check():
    return {"message": "ARM API"}
