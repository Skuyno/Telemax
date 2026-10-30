"""API Gateway service entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.router import router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    # Cross-origin JS (npm run dev, or NUXT_PUBLIC_API_BASE pointed straight
    # at this gateway) only sees the CORS-safelisted response headers unless
    # named here. Content-Disposition/Content-Range carry a file's name and
    # size (fetched via a one-byte Range request on a signed link) — without
    # this, the browser silently hides both from JS, same-origin deploys
    # (nginx) never notice since they don't go through CORS at all.
    expose_headers=["Content-Disposition", "Content-Range"],
)

app.include_router(router)
