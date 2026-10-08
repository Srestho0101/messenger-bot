import os
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from google import genai

app = FastAPI()

# Fetch environment variables
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "ndswqauigedaqty23bvgq8317y839erfiyh3n4hn09tr5g38ewy49h8hgy")

# Initialize the Google GenAI client (picks up GEMINI_API_KEY from Render env)
ai_client = genai.Client()

# ------------------------------------------------------------------
# Root Endpoint
# ------------------------------------------------------------------
@app.get("/")
async def root():
    return {"status": "ok", "message": "Messenger Bot with Gemini is active"}

# ------------------------------------------------------------------
# 1. GET /webhook -> Webhook Verification
# ------------------------------------------------------------------
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain", status_code=200)

    raise HTTPException(status_code=403, detail="Verification token mismatch")

# ------------------------------------------------------------------
# 2. POST /webhook -> Receive Incoming Messages & Generate AI Reply
# ------------------------------------------------------------------
@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                message = event.get("message")
                
                # Check that it's a standard user message (not an echo)
                if message and not message.get("is_echo") and "text" in message:
                    sender_psid = event["sender"]["id"]
                    user_text = message["text"]
                    print(f"[MESSAGE] Received from {sender_psid}: {user_text}")

                    # Generate AI response using Gemini
                    ai_reply = generate_gemini_response(user_text)

                    # Send reply back to user via Messenger
                    await send_text_message(sender_psid, ai_reply)

        return Response(content="EVENT_RECEIVED", status_code=200)

    raise HTTPException(status_code=404, detail="Unknown object type")

# ------------------------------------------------------------------
# Helper: Generate Response with Gemini
# ------------------------------------------------------------------
def generate_gemini_response(prompt: str) -> str:
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"[GEMINI ERROR] {e}")
        return "I am Groot. (Oops, my AI brain hit an error!)"

# ------------------------------------------------------------------
# Helper: Send Message via Meta Graph API
# ------------------------------------------------------------------
async def send_text_message(recipient_id: str, text: str):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "message": {"text": text},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        if response.status_code == 200:
            print("[REPLY] AI response sent successfully!")
        else:
            print(f"[REPLY ERROR] {response.status_code}: {response.text}")

# ------------------------------------------------------------------
# Entry Point for Production
# ------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
