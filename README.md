# 💬 Jolie Bot — AI Support Agent for Cosmetics

Jolie is a FastAPI-powered conversational assistant designed to help users discover skincare and haircare products based on their concerns. Built with OpenRouter’s DeepSeek Chat V3 model, Jolie combines emotional intelligence, modular architecture, and future extensibility for e-commerce integration.

---

## ⚙️ Architecture Overview

Client (Web or API Tester) ↓ FastAPI Backend (main.py) ↓ OpenRouter API (DeepSeek Chat V3) ↓ LLM Response → Returned to Client

Code

---

## 🧠 Core Logic

### 1. Environment Configuration

Sensitive credentials and model selection are stored in `.env`:

```env
MODEL=deepseek/deepseek-chat-v3-0324:free
OPENROUTER_API_KEY=your_api_key_here
Loaded via dotenv:

python
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("MODEL", "mistral/mistral-7b-instruct")
2. FastAPI Setup
CORS middleware allows frontend integration

/chat endpoint accepts POST requests with a user message

python
@app.post("/chat")
async def chat(request: ChatRequest):
    ...
3. System Prompt Injection
If the selected model includes "deepseek", a system prompt is injected to define Jolie’s tone and behavior:

python
system_prompt = {
    "role": "system",
    "content": "You are Jolie, a friendly and knowledgeable support agent for a cosmetics brand..."
}
This prompt is prepended to the message list sent to the LLM.

4. LLM Request Construction
The backend sends a POST request to OpenRouter’s /chat/completions endpoint:

python
response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": MODEL,
        "messages": [system_prompt, {"role": "user", "content": user_message}]
    }
)
5. Response Handling
The raw response from OpenRouter is returned directly to the client. Future versions may include filtering or formatting layers.

🧼 Code Hygiene
.gitignore excludes:

__pycache__/

*.pyc

Bytecode files removed from Git tracking

Commit history reflects iterative development and cleanup

🛍️ Roadmap
WooCommerce Integration Use REST API to fetch products based on user concerns

Guided Product Discovery Jolie will ask clarifying questions to refine recommendations

Session Awareness Track user preferences across interactions

Frontend Chat UI Embed Jolie into a branded website with real-time responses

📦 Installation
bash
git clone https://github.com/M8eda/Jolie-Bot.git
cd Jolie-Bot
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload
🧪 Testing
Use curl or Postman to test the /chat endpoint:

bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What’s good for dry skin?"}'
📫 Maintainer
Built by M8eda For issues, suggestions, or contributions, open a GitHub issue or pull request.

📝 License
Licensed under the Apache License 2.0. You may use, modify, and distribute this project freely under the terms of the license. See LICENSE for full details.
