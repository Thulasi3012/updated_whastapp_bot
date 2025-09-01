from fastapi import APIRouter, HTTPException,Query
from app.schemas.webhook import WebhookRequest
from fastapi.responses import PlainTextResponse
from app.services.llm_service import LLMService
from fastapi import HTTPException
import httpx

router = APIRouter(prefix="/api/chat", tags=["chat"])

llm_service = LLMService()


VERIFY_TOKEN = "your_secret_verify_token"  

@router.get("/webhook",response_class=PlainTextResponse)
def webhook(
    mode: str = Query(None, alias="hub.mode"),
    verify_token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge") 
):
    if mode == "subscribe" and verify_token == VERIFY_TOKEN:
        return challenge
    else:
        raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_message(request: WebhookRequest):
    data = request.dict()
    print("Received webhook data:", data)
    
    system_prompt = """
    You are a friendly and helpful WhatsApp chatbot designed to assist users with general inquiries. Your primary task is to acknowledge the user's message by repeating it back in a greeting format (e.g., 'hello! you said: [user's message]'), followed by a helpful or engaging response. Keep your tone casual and supportive, and adapt to the user's context if possible. If the input is unclear, ask for clarification politely.
    """

    try:
        message = data['entry'][0]['changes'][0]['value']['messages'][0]
        sender = message['from']
        text = message.get('text', {}).get('body', '')
        print(f"Message from {sender}: {text}")
        
        messages = [
            {"role": "user", "content": text}
        ]
        
        response = await llm_service.generate_chat_response(
            messages,
            system_prompt,
            None,
            use_fast_model=False,
            use_full_llm_mode=True
        )
        
        phone_number_id = "728278420370399"
        url = f'https://graph.facebook.com/v17.0/{phone_number_id}/messages'
        headers = {
            "Authorization": "Bearer EAAPJNBik8hkBPCxUDGLQBf98jRanlxwmMAXP2hxxif4ZAe1h0yUwcZANRqeaqBXF8rWZAayBbZAI6maM0Cn42hnLK9lyhDrTMbwS94SVE02pye4dVVVTjz9PMfwf4gT5fITeqG6DEh4cmQKv5Uf325UfJMz1I50JPAUoc8vlK2Q1eQ4ZABntrOnjaKiDC",
            "content-type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": sender,
            "type": "text",
            "text": {"body": response}
        }
        
      
        async with httpx.AsyncClient() as client:
            graph_response = await client.post(url, headers=headers, json=payload)
            graph_response.raise_for_status()  
        
        return {"status": "success", "message": "Message processed successfully"}
    
    except KeyError as e:
        return {"status": "error", "message": f"Missing key in webhook data: {str(e)}"}
    except httpx.HTTPStatusError as e:
        return {"status": "error", "message": f"Failed to send reply to Graph API: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}