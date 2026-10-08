import httpx
from fastapi import FastAPI, HTTPException, Query, Response, Request
from pydantic import BaseModel
from typing import List, Optional
import os
import uvicorn

app = FastAPI()

PAGE_ACCESS_TOKEN = "YOUR_PAGE_ACCESS_TOKEN_HERE"
VERIFY_TOKEN = "my_custom_secret_token_123"

# ------------------------------------------------------------------
# 1. GET /webhook -> Webhook Verification
# ------------------------------------------------------------------
@app.get("/webhook")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_token == VERIFY_TOKEN:
        print("WEBHOOK_VERIFIED")
        # Return raw challenge string as plain text with 200 OK
        return Response(content=hub_challenge, media_type="text/plain", status_code=200)
    
    raise HTTPException(status_code=403, detail="Verification token mismatch")

# ------------------------------------------------------------------
# 2. POST /webhook -> Receiving Messages
# ------------------------------------------------------------------
@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            messaging_events = entry.get("messaging", [])
            for event in messaging_events:
                # Ensure it's a user message and not an echo from the page
                message = event.get("message")
                if message and not message.get("is_echo"):
                    sender_psid = event["sender"]["id"]
                    print(f"Received message from PSID: {sender_psid}")
                    
                    # Reply with static text
                    await send_text_message(sender_psid, "I am Groot.")

        return Response(content="EVENT_RECEIVED", status_code=200)

    raise HTTPException(status_code=404, detail="Unknown object type")

# ------------------------------------------------------------------
# Helper: Call Meta Graph API asynchronously
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
            print('Reply "I am Groot." sent successfully!')
        else:
            print(f"Failed to send message: {response.status_code} - {response.text}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
