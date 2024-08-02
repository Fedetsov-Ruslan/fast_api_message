import os
import logging
import uvicorn
import redis

from typing import List
from fastapi import FastAPI, Request
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGO_URL")
redis_client = redis.from_url("redis://redis:6379/0")

class MessageContent(BaseModel):
    content: str
    user_name: str


client = AsyncIOMotorClient(MONGODB_URL)
app = FastAPI()
app.state.mongo_client = client

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

@app.get("/api/v1/messages/", response_model=dict)
async def get_messages(request: Request):
    mongo_client: AsyncIOMotorClient = request.app.state.mongo_client["message_database"]
    cursor = mongo_client.messages.find({})
    res = []
    users = []
    for message in await cursor.to_list(length=None):
        res.append(message["content"])
        users.append(message["user_name"])
    response = {"messages": res, "users": users}
    return response

@app.post("/api/v1/message/")
async def create_message(request: Request, message: MessageContent):   
    mongo_client: AsyncIOMotorClient = request.app.state.mongo_client["message_database"]
    await mongo_client.messages.insert_one({"content": message.content, "user_name": message.user_name})
    logging.info(f"Received message: {message.content}")

    redis_client.set("last_message", f"{message.user_name}: {message.content}")
    return {"message": "Message created successfully", "content": message.content}


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    )
    uvicorn.run(app, host="0.0.0.0", port=8001)