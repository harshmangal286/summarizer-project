from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router


app = FastAPI()

# CORS: allow the React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Backend is running!"}


# Mount all API routes at the root (no prefix)
app.include_router(router)
