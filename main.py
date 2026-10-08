import os
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response

app = FastAPI()

# Fetch environment variables from Render (or defaults for testing)
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "ndswqauigedaqty23bvgq8317y839erfiyh3n4hn09tr5g38ewy49h8hgy")

# ------------------------------------------------------------------
# Root Endpoint (Optional sanity check)
# ------------------------------------------------------------------
@app.get("/")
async def root():
    return {"status": "ok", "message": "Messenger Bot is active"}

# ------------------------------------------------------------------
# 1. GET /webhook -> Webhook Verification
# ------------------------------------------------------------------
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    print(f"[VERIFY] Received mode: {mode}, token: {token}")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("[VERIFY] Verification SUCCESS! Returning challenge.")
        # Must return raw challenge string with text/plain content-type and 200 OK status
        return Response(content=challenge, media_type="text/plain", status_code=200)

    print("[VERIFY] Verification FAILED! Token or mode mismatch.")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

# ------------------------------------------------------------------
# 2. POST /webhook -> Receive Incoming Messages
# ------------------------------------------------------------------
@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                message = event.get("message")
                
                # Check that it's a standard user message (not an echo sent by the page)
                if message and not message.get("is_echo"):
                    sender_psid = event["sender"]["id"]
                    print(f"[POST] Received message from PSID: {sender_psid}")

                    # Reply with "I am Groot."
                    await send_text_message(sender_psid, "I am Groot.")

        return Response(content="EVENT_RECEIVED", status_code=200)

    raise HTTPException(status_code=404, detail="Unknown object type")

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
            print("[REPLY] 'I am Groot.' sent successfully!")
        else:
            print(f"[REPLY ERROR] {response.status_code}: {response.text}")

# ------------------------------------------------------------------
# Entry Point for Production (Render PORT binding)
# ------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)