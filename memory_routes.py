from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv
import os

# ✅ Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ✅ Validate credentials
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("❌ Supabase credentials missing. Check your .env file.")

# ✅ Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

# ✅ Memory schema
class MemorySchema(BaseModel):
    user_id: str
    skin_type: str = None
    preferences: dict = {}
    language: str = None
    tone_profile: dict = {}
    meta: dict = {}

# ✅ Create memory
@router.post("/memory/create")
def create_memory(memory: MemorySchema):
    try:
        response = supabase.table("jolie_bot_memory").insert({
            "name": memory.user_id,
            "skin_type": memory.skin_type,
            "preferences": memory.preferences,
            "language": memory.language,
            "tone_profile": memory.tone_profile,
            "meta": memory.meta
        }).execute()

        if response.data:
            return {"status": "Memory created ✅", "data": response.data}
        else:
            raise HTTPException(status_code=500, detail="Supabase insert returned no data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase error: {str(e)}")

# ✅ Update memory
@router.put("/memory/update")
def update_memory(memory: MemorySchema):
    try:
        response = supabase.table("jolie_bot_memory").update({
            "skin_type": memory.skin_type,
            "preferences": memory.preferences,
            "language": memory.language,
            "tone_profile": memory.tone_profile,
            "meta": memory.meta
        }).eq("name", memory.user_id).execute()

        if response.data:
            return {"status": "Memory updated ✅", "data": response.data}
        else:
            raise HTTPException(status_code=500, detail="Supabase update returned no data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase error: {str(e)}")

# ✅ Delete memory
@router.delete("/memory/delete/{user_id}")
def delete_memory(user_id: str):
    try:
        response = supabase.table("jolie_bot_memory").delete().eq("name", user_id).execute()

        if response.data:
            return {"status": f"Memory for {user_id} deleted ✅"}
        else:
            raise HTTPException(status_code=404, detail="Memory not found or already deleted")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase error: {str(e)}")

# ✅ Get memory
@router.get("/memory/{user_id}")
def get_memory(user_id: str):
    try:
        response = supabase.table("jolie_bot_memory").select("*").eq("name", user_id).execute()

        if response.data:
            return {"status": "Memory fetched ✅", "data": response.data[0]}
        else:
            raise HTTPException(status_code=404, detail="Memory not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase error: {str(e)}")

# ✅ Health check
@router.get("/memory/healthcheck")
def memory_healthcheck():
    try:
        response = supabase.table("jolie_bot_memory").select("name").limit(1).execute()
        return {"status": "Supabase connection ✅"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase error: {str(e)}")