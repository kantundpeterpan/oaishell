from fastapi import FastAPI, Header, Query, Path, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import uvicorn

app = FastAPI(title="OAI-Shell Dummy Server")

# Models for testing nested structures
class ItemDetails(BaseModel):
    color: str
    weight: float

class Item(BaseModel):
    name: str
    details: ItemDetails

# 1. Basic Health
@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

# 2. Login (State Extraction Test)
@app.post("/auth/login")
def login(username: str = Body(...), password: str = Body(...)):
    return {
        "access_token": "mock-token-123",
        "session_id": "session-456",
        "user": {"name": username}
    }

# 3. Path Parameters Test
@app.get("/users/{user_id}")
def get_user(user_id: str = Path(...)):
    return {"id": user_id, "name": f"User {user_id}", "role": "admin"}

# 4. Nested Body & Type Inference Test
@app.post("/items")
def create_item(item: Item):
    return {"message": "Item created", "received": item}

# 5. Query & Header Test
@app.get("/search")
def search(
    q: str = Query(...), 
    limit: int = Query(10),
    x_api_key: str = Header(..., alias="X-API-Key")
):
    return {
        "query": q,
        "limit": limit,
        "header_received": x_api_key
    }

# 6. Streaming Test
async def dummy_event_generator():
    for i in range(5):
        yield f"data: Progress {i*20}%\n\n"
        await asyncio.sleep(0.5)
    yield "data: Complete\n\n"

@app.get("/stream")
async def stream():
    return StreamingResponse(dummy_event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
