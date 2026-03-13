import os
import json
import asyncio
import xml.etree.ElementTree as ET
import html
from datetime import datetime
from typing import Dict, Any

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration Loading ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek").lower()

# API Keys
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# API URLs and Models
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL") # Must be set if using Ollama

app = FastAPI()

# System prompt for DeepSeek
SYSTEM_PROMPT = """You are a world-class diagram generation assistant. Your primary goal is to create valid, visually appealing mxGraphModel XML for draw.io.

**Aesthetic Principles:**
- **Visually Engaging:** Go beyond basic layouts. Use colors, appropriate shapes (ellipses, cylinders, etc.), and logical grouping to make diagrams clear and professional.
- **Color Palette:** Apply a tasteful and consistent color scheme. For example, use one color for actions, another for decisions, etc.
- **Smart Layout:** Ensure elements are well-spaced and aligned. Avoid clutter and overlapping.

**Generation & Modification Task:**
1.  **Generation:** If asked to create a diagram, generate the complete XML applying the aesthetic principles above.
2.  **Modification:** If given a `<diagram>` and `<request>`, modify the existing XML, preserving the overall style.

**CRITICAL TECHNICAL REQUIREMENTS:**
- Your response MUST BE ONLY the raw mxGraphModel XML string.
- Absolutely NO conversational text, explanations, comments, or markdown.
- The response must start with '<mxGraphModel' and end with '</mxGraphModel>'.
"""

def clean_xml_content(xml_content: str, chat_history: list) -> str | None:
    """Clean and normalize XML content from DeepSeek, and validate its structure."""
    original_xml = xml_content
    print(f"[CLEANING] Starting cleaning. Input length: {len(xml_content)}")
    
    # First, un-escape any potential HTML entities like &lt;
    xml_content = html.unescape(xml_content)
    
    # Simple prefix/suffix cleaning
    if xml_content.lower().startswith("```xml"):
        xml_content = xml_content[6:]
    elif xml_content.lower().startswith("```"):
        xml_content = xml_content[3:]
    if xml_content.lower().endswith("```"):
        xml_content = xml_content[:-3]
    xml_content = xml_content.strip()
    if xml_content.lower().startswith("<?xml"):
        end_decl = xml_content.find("?>")
        if end_decl != -1:
            xml_content = xml_content[end_decl + 2:].strip()

    # Find the main mxGraphModel tags, case-insensitively
    start_pos = xml_content.lower().find('<mxgraphmodel')
    end_pos = xml_content.lower().rfind('</mxgraphmodel>')

    if start_pos == -1 or end_pos == -1:
        print(f"[CLEANING] No complete <mxGraphModel> tags found. Assuming text response.")
        return None

    # Extract content between the first opening and last closing tag
    xml_content = xml_content[start_pos : end_pos + len('</mxGraphModel>')]
    
    # Before returning, do a final validation by parsing the XML
    try:
        ET.fromstring(xml_content)
        print("[VALIDATION] XML is well-formed. Returning content.")
        return xml_content
    except ET.ParseError as e:
        print(f"[VALIDATION] Final XML is malformed: {e}. Returning error diagram.")
        log_error_to_feedback(
            error_type="XMLParseError",
            error_message=f"The cleaned XML could not be parsed. Error: {e}\n\nCleaned XML (first 500 chars):\n{xml_content[:500]}",
            chat_history=chat_history,
            source="Backend"
        )
        # Sanitize error message for display
        error_message = str(e).replace('<', '').replace('>', '')
        return f'''<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <mxCell id="2" value="XML Parse Error" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffcccc;strokeColor=#ff0000;fontSize=16;" vertex="1" parent="1">
      <mxGeometry x="100" y="100" width="300" height="100" as="geometry"/>
    </mxCell>
    <mxCell id="3" value="{error_message}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=12;" vertex="1" parent="1">
      <mxGeometry x="100" y="220" width="300" height="60" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>'''

def log_error_to_feedback(error_type: str, error_message: str, chat_history: list = None, source: str = "Backend"):
    """Appends error details and context to feedback.md."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    context_str = ""
    if source == "Backend" and chat_history:
        # Convert chat history to a readable string
        history_log = "\n".join([f"- **{msg['role']}**: {str(msg['content'])[:250]}..." for msg in chat_history[-5:]])
        context_str = f"""**Chat History (Last 5 Messages):**
{history_log}"""
    elif source == "Client":
        context_str = "**Context:** This error originated from the client-side (browser)."

    feedback_entry = f"""
---
### 🚨 New {source} Error Logged: {timestamp}

**Error Type:** `{error_type}`

**Error Message:**
```json
{error_message}
```

{context_str}
"""
    try:
        with open("feedback.md", "a", encoding="utf-8") as f:
            f.write(feedback_entry)
        print("[FEEDBACK] Error details logged to feedback.md")
    except Exception as e:
        print(f"[FEEDBACK] CRITICAL: Failed to write to feedback.md: {e}")

async def call_llm_api(messages: list) -> str:
    """Call the configured LLM API to generate diagram XML."""
    api_url = ""
    headers = {"Content-Type": "application/json"}
    model = ""
    
    if LLM_PROVIDER == "deepseek":
        api_url = "https://api.deepseek.com/chat/completions"
        model = DEEPSEEK_MODEL
        if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "your_api_key_here":
            raise ValueError("DEEPSEEK_API_KEY not found or not set in .env file")
        headers["Authorization"] = f"Bearer {DEEPSEEK_API_KEY}"
    
    elif LLM_PROVIDER == "openai":
        api_url = "https://api.openai.com/v1/chat/completions"
        model = OPENAI_MODEL
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_api_key_here":
            raise ValueError("OPENAI_API_KEY not found or not set in .env file")
        headers["Authorization"] = f"Bearer {OPENAI_API_KEY}"

    elif LLM_PROVIDER == "ollama":
        api_url = OLLAMA_API_URL
        model = OLLAMA_MODEL
        if not model:
            raise ValueError("OLLAMA_MODEL must be set in .env file when using Ollama provider")
    
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: '{LLM_PROVIDER}'. Use 'deepseek', 'openai', or 'ollama'.")

    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }

    print(f"Sending request to {LLM_PROVIDER} API ({api_url}) with model {model}...")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(api_url, headers=headers, json=payload)
            print(f"Response status: {response.status_code}")
            response.raise_for_status()
            result = response.json()

            if LLM_PROVIDER == "ollama":
                raw_content = result["message"]["content"].strip()
            else: # OpenAI-compatible response structure
                raw_content = result["choices"][0]["message"]["content"].strip()

        print(f"Received API content (first 200 chars): {raw_content[:200]}...")
        
        cleaned_xml = clean_xml_content(raw_content, chat_history=messages)
        
        if cleaned_xml is None:
            return f"TEXT_RESPONSE::{raw_content}"
        
        return cleaned_xml

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error from {LLM_PROVIDER}: {e.response.status_code} - {e.response.text}"
        print(f"API error: {error_msg}")
        raise
    except Exception as e:
        print(f"Unexpected error calling {LLM_PROVIDER} API: {e}")
        raise

@app.get("/")
async def get_index():
    """Serve the main HTML page."""
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Handle browser's request for a favicon to prevent 404 errors in logs."""
    return Response(status_code=204)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time diagram updates with chat history."""
    await websocket.accept()
    print("WebSocket connection accepted. Initializing chat history.")
    
    # Each connection gets its own stateful chat history
    chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    try:
        while True:
            # Receive data from client
            data = await websocket.receive_text()
            
            try:
                # The client might send JSON with prompt and currentXml, or just a plain prompt.
                # We only need the prompt now.
                try:
                    payload = json.loads(data)

                    # Check if it's a client-side error report
                    if payload.get('type') == 'client-error':
                        error_details = payload.get('error', {})
                        # The error message can be a JSON string of the details
                        error_message_str = json.dumps(error_details, indent=2)
                        
                        log_error_to_feedback(
                            error_type="ClientSideJavaScriptError", 
                            error_message=error_message_str, 
                            source="Client"
                        )
                        print("[FEEDBACK] Client-side error logged.")
                        continue # Wait for next message

                    prompt = payload.get('prompt', '')
                    print(f"Received JSON payload. Using prompt: {prompt[:50]}...")

                except json.JSONDecodeError:
                    # Backward compatibility: if it's not JSON, treat as plain prompt
                    prompt = data
                    print(f"Received plain prompt: {prompt[:50]}...")

                if not prompt:
                    continue

                # Add user's new prompt to the history
                chat_history.append({"role": "user", "content": prompt})
                
                # Call DeepSeek API with the full conversation history
                response_content = await call_llm_api(chat_history)
                
                if response_content.startswith("TEXT_RESPONSE::"):
                    text_message = response_content.split("TEXT_RESPONSE::", 1)[1]
                    print(f"Sending text response to client: {text_message[:100]}...")
                    chat_history.append({"role": "assistant", "content": text_message})
                    await websocket.send_json({'type': 'text', 'content': text_message})
                else:
                    # It's XML
                    xml_content = response_content
                    print(f"Generated XML (first 100 chars): {xml_content[:100]}...")
                    chat_history.append({"role": "assistant", "content": xml_content})
                    await websocket.send_json({'type': 'xml', 'content': xml_content})
                
            except ValueError as e:
                error_msg = f"Error: {str(e)}. Please check your API key in .env file."
                print(f"ValueError: {error_msg}")
                log_error_to_feedback("ValueError", error_msg, chat_history)
                await websocket.send_json({'type': 'error', 'content': error_msg})
            except Exception as e:
                error_msg = f"Failed to generate diagram: {str(e)}"
                print(f"Exception: {error_msg}")
                log_error_to_feedback(type(e).__name__, error_msg, chat_history)
                await websocket.send_json({'type': 'error', 'content': error_msg})
                
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_text(f"ERROR: Connection error: {str(e)}")
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)