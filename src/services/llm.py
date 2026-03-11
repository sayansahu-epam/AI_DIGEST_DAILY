"""
LLM client for Ollama.
Provides simple interface to chat with local Llama 3 model.
"""

import json
import logging
import urllib.request
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Ollama API configuration
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3:8b"
TIMEOUT_SECONDS = 120  # LLM can be slow


@dataclass
class LLMResponse:
    """Response from the LLM."""
    content: str
    success: bool
    error: Optional[str] = None


def chat(prompt: str, temperature: float = 0.1) -> LLMResponse:
    """
    Send a prompt to Ollama and get a response.
    
    Args:
        prompt: The text to send to the LLM
        temperature: Creativity level (0.0 = deterministic, 1.0 = creative)
    
    Returns:
        LLMResponse with content or error
    """
    url = f"{OLLAMA_BASE_URL}/api/chat"
    
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }
    
    try:
        # Prepare request
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        # Send request
        logger.debug("Sending prompt to Ollama (length=%d)", len(prompt))
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
        
        # Extract content
        content = response_data.get("message", {}).get("content", "")
        
        if not content:
            return LLMResponse(
                content="",
                success=False,
                error="Empty response from LLM"
            )
        
        logger.debug("Received response (length=%d)", len(content))
        return LLMResponse(content=content, success=True)
        
    except urllib.error.URLError as e:
        error_msg = f"Cannot connect to Ollama: {e}"
        logger.error(error_msg)
        return LLMResponse(content="", success=False, error=error_msg)
        
    except Exception as e:
        error_msg = f"LLM request failed: {e}"
        logger.error(error_msg)
        return LLMResponse(content="", success=False, error=error_msg)




def _extract_json(text: str) -> str | None:
    """
    Extract JSON from LLM response.
    Handles various formats like markdown code blocks, extra text, etc.
    """
    import re
    
    # Method 1: Try to find JSON in markdown code block
    # Matches ```json ... ``` or ``` ... ```
    code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    matches = re.findall(code_block_pattern, text)
    if matches:
        for match in matches:
            candidate = match.strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                return candidate
    
    # Method 2: Find content between first { and last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace:last_brace + 1]
        # Basic validation - check if it looks like JSON
        if candidate.count("{") >= 1 and candidate.count("}") >= 1:
            return candidate
    
    # Method 3: If text itself starts with { and ends with }
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    
    return None





def chat_json(prompt: str, temperature: float = 0.1) -> dict | None:
    """
    Send a prompt expecting JSON response.
    Parses the response and returns a dict, or None on failure.
    """
    response = chat(prompt, temperature)
    
    if not response.success:
        logger.error("LLM failed: %s", response.error)
        return None
    
    content = response.content.strip()
    
    # Try to extract JSON from various formats
    json_str = _extract_json(content)
    
    if json_str is None:
        logger.error("Could not find JSON in LLM response")
        logger.debug("Raw content: %s", content[:500])
        return None
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON from LLM: %s", e)
        logger.debug("Extracted JSON string: %s", json_str[:500])
        return None


def is_ollama_running() -> bool:
    """Check if Ollama server is running and accessible."""
    try:
        url = f"{OLLAMA_BASE_URL}/api/tags"
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_available_models() -> list[str]:
    """Get list of models available in Ollama."""
    try:
        url = f"{OLLAMA_BASE_URL}/api/tags"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = data.get("models", [])
            return [m.get("name", "") for m in models]
    except Exception as e:
        logger.error("Failed to get models: %s", e)
        return []


# ---------------------------------------------------------------------------
# Quick Test (run this file directly to test)
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print("=" * 60)
    print("  Testing LLM Client (Ollama)")
    print("=" * 60)
    
    # Test 1: Check if Ollama is running
    print("\n🔍 Test 1: Checking Ollama connection...")
    if is_ollama_running():
        print("   ✅ Ollama is running!")
    else:
        print("   ❌ Ollama is NOT running!")
        print("   Please start Ollama and try again.")
        exit(1)
    
    # Test 2: List available models
    print("\n📋 Test 2: Available models...")
    models = get_available_models()
    for model in models:
        print(f"   - {model}")
    
    # Test 3: Simple chat
    print("\n💬 Test 3: Simple chat...")
    response = chat("Say 'Hello from Llama!' and nothing else.")
    if response.success:
        print(f"   ✅ Response: {response.content}")
    else:
        print(f"   ❌ Error: {response.error}")
    
    # Test 4: JSON response
    print("\n📦 Test 4: JSON response...")
    json_prompt = """
    Respond with ONLY valid JSON, no other text:
    {
        "status": "working",
        "message": "Hello from Llama!"
    }
    """
    result = chat_json(json_prompt)
    if result:
        print(f"   ✅ Parsed JSON: {result}")
    else:
        print("   ❌ Failed to parse JSON")
    
    print("\n" + "=" * 60)
    print("  ✅ All tests complete!")
    print("=" * 60)