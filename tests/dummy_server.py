from fastapi import FastAPI, Header, Query, Path, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict
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

class NestedInfo(BaseModel):
    tags: List[str]
    score: float

class ComplexItem(BaseModel):
    id: int
    data: List[NestedInfo]

class ActionResponse(BaseModel):
    status: str
    action_id: str
    affected_user: str

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

class ItemResponse(BaseModel):

    message: str = "message"
    received: Item

@app.post("/items")
def create_item(item: Item) -> ItemResponse:
    return ItemResponse(received = Item)

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

@app.get("/complex", response_model=List[ComplexItem])
def get_complex():
    return [
        {
            "id": 1,
            "data": [
                {"tags": ["a", "b"], "score": 0.9},
                {"tags": ["c"], "score": 0.5}
            ]
        }
    ]

# 8. POST with Path Params
@app.post("/users/{user_id}/actions", response_model=ActionResponse)
def user_action(user_id: str, action: str = Body(...)):
    return {
        "status": "executed",
        "action_id": f"act-{action}",
        "affected_user": user_id
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
