from memory_routes import router as memory_router
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
from dotenv import load_dotenv
import requests
import os
import time
import re
from textblob import TextBlob

# ✅ Load environment variables
load_dotenv()

# ✅ Initialize FastAPI app
app = FastAPI()
app.include_router(memory_router)

# ✅ Enable CORS for frontend/backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this to your frontend domain later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ LLM Config
API_KEY = os.getenv("LLM_API_KEY")
MODEL = os.getenv("LLM_MODEL", "mixtral-8x7b-32768")
API_BASE = os.getenv("LLM_API_BASE", "https://api.groq.com/openai/v1")

# ✅ Supabase Config
SUPABASE_API_TOKEN = os.getenv("SUPABASE_API_TOKEN")
SUPABASE_PROJECT_ID = os.getenv("SUPABASE_PROJECT_ID")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE")
SUPABASE_REST_URL = f"https://{SUPABASE_PROJECT_ID}.supabase.co/rest/v1/{SUPABASE_TABLE}"

# ✅ Request Models
class ChatRequest(BaseModel):
    message: str
    email: Optional[str] = None
    session_id: Optional[str] = None

class MemoryEntry(BaseModel):
    email: str
    name: Optional[str] = None
    language: Optional[str] = None
    skin_type: Optional[str] = None
    tone_profile: Optional[Dict] = None
    preferences: Optional[Dict] = None
    meta: Optional[Dict] = None
    timestamp: Optional[str] = None

class MemoryUpdate(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None
    skin_type: Optional[str] = None
    tone_profile: Optional[Dict] = None
    preferences: Optional[Dict] = None
    meta: Optional[Dict] = None



# ✅ Retry logic for LLM requests
def send_request_with_retry(payload, headers, retries=2, delay=3):
    for attempt in range(retries):
        try:
            start_time = time.time()
            response = requests.post(
                f"{API_BASE}/chat/completions",
                headers=headers,
                json=payload,
                timeout=20
            )
            duration = time.time() - start_time
            print(f"⏱️ Groq response time: {duration:.2f} seconds")
            return response
        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout on attempt {attempt + 1}, retrying in {delay}s...")
            time.sleep(delay)
    raise Exception("All retries failed")

# ✅ Extract memory fields from user message
def extract_memory_fields(message: str) -> Dict:
    memory = {}
    # Preserve names exactly as typed (no autocorrect)
    name_match = re.search(r"\bmy name is ([A-Za-z\-']+)", message, re.IGNORECASE)
    skin_match = re.search(r"\bi have (\w+) skin", message, re.IGNORECASE)
    fragrance_match = re.search(r"\bi like (\w+) fragrance", message, re.IGNORECASE)
    texture_match = re.search(r"\bi prefer (\w+) texture", message, re.IGNORECASE)

    if name_match:
        raw_name = name_match.group(1)
        memory["name"] = raw_name.strip()  # No autocorrect
    if skin_match:
        memory["skin_type"] = skin_match.group(1).lower()
    
    prefs = {}
    if fragrance_match:
        prefs["fragrance"] = fragrance_match.group(1).lower()
    if texture_match:
        prefs["texture"] = texture_match.group(1).lower()
    if prefs:
        memory["preferences"] = prefs

    return memory

# ✅ Fetch user memory from Supabase
def fetch_user_memory(email: str):
    headers = {
        "apikey": SUPABASE_API_TOKEN,
        "Authorization": f"Bearer {SUPABASE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    params = {
        "select": "*",
        "email": f"eq.{email}",
        "limit": "1"
    }
    response = requests.get(SUPABASE_REST_URL, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        return data[0] if data else None
    return None

# ✅ Detect user intent from message
def detect_intent(message: str) -> str:
    message = message.lower()
    if any(term in message for term in ["routine", "develop", "steps", "regimen", "morning", "evening", "template", "ritual"]):
        return "routine_building"
    if any(term in message for term in ["dry", "oily", "acne", "sensitive", "redness", "breakout", "eczema", "texture", "irritation"]):
        return "skin_issue"
    if any(term in message for term in ["hair", "scalp", "frizz", "volume", "split ends", "damage", "hydration", "curl", "shine"]):
        return "hair_issue"
    return "general"


# ✅ Helper: Smart tone filter — keep replies tight and actionable
def tone_filter(text: str) -> str:
    sentences = re.split(r'(?<=[.!?]) +', text.strip())
    trimmed = " ".join(sentences[:2])
    if "recommend" not in trimmed.lower() and "routine" not in trimmed.lower():
        trimmed += " Would you like product recommendations or routine tips?"
    return trimmed + " 💡"

# ✅ Chat Function
@app.post("/chat")
async def chat(request: ChatRequest):
    # ✅ Clean and normalize input (no autocorrect on names)
    raw_message = request.message.strip()
    cleaned_message = ''.join(c for c in raw_message if c.isalnum() or c.isspace())
    user_message = cleaned_message.lower()

    # ✅ Handle playful skin types
    if "hulk skin" in user_message:
        user_message = user_message.replace("hulk skin", "sensitive skin")

    extracted = extract_memory_fields(user_message)
    memory_response = None
    user_memory = None

    # ✅ Fetch memory if email provided
    if request.email:
        user_memory = fetch_user_memory(request.email)

    # ✅ Step 1: Greeting detection
    if re.search(r"\b(hi|hello|hey|start)\b", user_message) and not user_memory:
        return {
            "reply": (
                "Hey 👋 Let’s get you glowing.\n"
                "Can you tell me your name and skin type so I can tailor everything to you?"
            )
        }

    # ✅ Step 2: Capture name + skin type if missing
    if request.email and not user_memory and ("name" in extracted or "skin_type" in extracted):
        memory_payload = {
            "email": request.email,
            **extracted,
            "meta": {
                "source": "chatbot",
                "session_id": request.session_id or "unknown"
            }
        }
        headers = {
            "apikey": SUPABASE_API_TOKEN,
            "Authorization": f"Bearer {SUPABASE_API_TOKEN}",
            "Content-Type": "application/json"
        }
        memory_response = requests.post(SUPABASE_REST_URL, headers=headers, json=memory_payload)
        return {
            "reply": (
                "Perfect 🌟 I’ve saved your profile.\n"
                "Now tell me — are you looking to improve your routine or solve a specific issue?"
            )
        }

    # ✅ Step 3: Build system prompt with strict persona enforcement
    intent = detect_intent(user_message)
    system_prompt = {
        "role": "system",
        "content": (
            "You are Jolie, a warm, confident, emotionally intelligent beauty assistant. "
            "You never say 'I am Jolie' or introduce yourself repeatedly. "
            "You speak with clarity, empathy, and directness. "
            "Always offer actionable advice, product suggestions, or routine templates. "
            "Avoid generic chatbot language. Stay human, helpful, and bold."
        )
    }


    # ✅ Inject memory traits into system prompt
    if user_memory:
        traits = []
        if user_memory.get("name"):
            traits.append(f"name: {user_memory['name']}")
        if user_memory.get("skin_type"):
            traits.append(f"skin type: {user_memory['skin_type']}")
        if user_memory.get("preferences"):
            prefs = ", ".join(f"{k}: {v}" for k, v in user_memory["preferences"].items())
            traits.append(f"preferences: {prefs}")
        memory_summary = "User profile: " + "; ".join(traits)
        system_prompt["content"] += f" {memory_summary}"

    # ✅ Intent-specific guidance — enforce direct behavior
    if intent == "routine_building":
        system_prompt["content"] += (
            " The user wants help building a skincare or haircare routine. "
            "Ask what they currently use in the morning and evening. "
            "Then recommend a 3-step routine with specific product types: cleanser, treatment, and moisturizer or conditioner. "
            "Speak in short, confident sentences. "
            "End with: 'Would you like me to suggest actual products next?'"
        )
    elif intent == "skin_issue":
        system_prompt["content"] += (
            " The user has a skin concern. Ask about their skin type and current routine. "
            "Then recommend 2–3 product types or steps to address the issue. "
            "Speak clearly and professionally. "
            "End with: 'Want me to suggest specific products for this?'"
        )
    elif intent == "hair_issue":
        system_prompt["content"] += (
            " The user has a hair concern. Ask about their hair texture and goals (e.g., volume, hydration, damage repair). "
            "Then suggest a care routine or product category. "
            "Be direct and helpful. "
            "End with: 'Would you like product suggestions for your hair type?'"
        )

    # ✅ Prepare model payload
    messages = [system_prompt, {"role": "user", "content": user_message}]
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 300,
        "stream": False
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    response = send_request_with_retry(payload, headers)
    reply = response.json()

    # ✅ Tone filter — trim overly long replies but keep useful content
    if "choices" in reply and reply["choices"]:
        content = reply["choices"][0]["message"]["content"]
        if len(content) > 500:
            reply["choices"][0]["message"]["content"] = tone_filter(content)

    # ✅ Future-ready product hook
    if intent in ["skin_issue", "hair_issue", "routine_building"]:
        reply["choices"][0]["message"]["content"] += (
            "\n\n🛍️ Soon I’ll be able to recommend products directly from our shop. For now, I can guide you with routines and care tips tailored to your needs."
        )

    # ✅ Memory confirmation
    if memory_response and memory_response.status_code in [200, 201]:
        reply["jolie_memory"] = "Profile updated ✅"

    return reply