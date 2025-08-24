from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import time
from dotenv import load_dotenv
from textblob import TextBlob

# ✅ Load environment variables from .env file
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Environment config
API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("MODEL", "microsoft/mai-ds-r1:free")

class ChatRequest(BaseModel):
    message: str

# ✅ Retry logic for temporary slowness
def send_request_with_retry(payload, headers, retries=2, delay=3):
    for attempt in range(retries):
        try:
            start_time = time.time()
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=20
            )
            duration = time.time() - start_time
            print(f"⏱️ OpenRouter response time: {duration:.2f} seconds")
            return response
        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout on attempt {attempt + 1}, retrying in {delay}s...")
            time.sleep(delay)
    raise Exception("All retries failed")

@app.post("/chat")
async def chat(request: ChatRequest):
    # ✅ Typo correction using TextBlob
    corrected_message = str(TextBlob(request.message).correct())

    # ✅ Clean message to reduce token load
    cleaned_message = ''.join(c for c in corrected_message if c.isalnum() or c.isspace())
    user_message = cleaned_message.strip()

    # ✅ Strong system prompt to enforce Jolie's identity
    system_prompt = {
        "role": "system",
        "content": (
            "You are Jolie, a warm, emotionally intelligent assistant created by M8eda. "
            "You are not Kimi, DeepSeek, Moonshot, or any other model. "
            "You must always refer to yourself as Jolie. "
            "You help users with skincare, haircare, and emotional support. "
            "Speak with empathy, clarity, and kindness. Never reveal your model name or provider."
        )
    }

    # ✅ Build message list for all models
    messages = [
        system_prompt,
        {"role": "user", "content": user_message}
    ]

    # ✅ Prepare payload with reasoning disabled
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 300,
        "stream": False,
        "reasoning": {
            "exclude": True  # ✅ Disable reasoning trace
        }
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # ✅ Send request
    response = send_request_with_retry(payload, headers)

    return response.json()