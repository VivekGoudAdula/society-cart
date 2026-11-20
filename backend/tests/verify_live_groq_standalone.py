"""Standalone live verification script for Groq API integration.

Runs ONLY live Groq API calls when GROQ_API_KEY is configured.
Keeps live integration testing completely separate from fast, deterministic unit test fixtures.
"""

import asyncio
import json
import os
import sys
from dotenv import dotenv_values
from groq import AsyncGroq

# Resolve backend .env
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
cfg = dotenv_values(ENV_PATH)
API_KEY = cfg.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
MODEL = cfg.get("GROQ_MODEL") or os.environ.get("GROQ_MODEL") or "openai/gpt-oss-120b"


async def run_live_tests():
    if not API_KEY or not API_KEY.strip():
        print("[-] GROQ_API_KEY is not configured. Live integration cannot run.")
        sys.exit(1)

    print(f"[+] Initializing Groq client with model: {MODEL}")
    client = AsyncGroq(api_key=API_KEY.strip(), timeout=30.0)

    test_cases = [
        {
            "lang": "English",
            "text": "Please add 2 loaves of whole wheat bread, 1 kg tomatoes, and 6 eggs",
        },
        {
            "lang": "Telugu",
            "text": "నాకు 5 కిలోల బియ్యం (సోనా మసూరి), 2 లీటర్ల విజయ పాలు, 1 కేజీ కందిపప్పు కావాలి",
        },
        {
            "lang": "Hindi",
            "text": "मुझे 2 किलो आटा (आशीर्वाद), 1 लीटर सरसों का तेल और 500 ग्राम पनीर चाहिए",
        },
        {
            "lang": "Mixed Code-Switching",
            "text": "1 kg toor dal teesko, 2 packets curd and thoda coriander also",
        },
    ]

    system_prompt = """You are the AI Grocery Parser for Society Cart. Extract grocery requirements into a valid JSON object with:
- detected_language: ("en" | "te" | "hi" | "mixed")
- items: list of {id, original_name, normalized_name, quantity, unit, category, brand, variant, confidence, needs_clarification, clarification_reason}
- overall_status: ("pending_review" | "needs_clarification")
- clarification_prompt: string or null
Respond ONLY with valid JSON."""

    success_count = 0
    for tc in test_cases:
        print(f"\n--- Testing {tc['lang']} ---")
        print(f"Input: {tc['text']}")
        try:
            res = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract grocery requirements from this message:\n\"\"\"{tc['text']}\"\"\""},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=800,
            )
            raw_content = res.choices[0].message.content
            parsed = json.loads(raw_content)
            items = parsed.get("items", [])
            status = parsed.get("overall_status", "pending_review")
            print(f"[✓] Status: {status} | Language: {parsed.get('detected_language')} | Items: {len(items)}")
            for idx, it in enumerate(items, 1):
                print(f"    {idx}. {it.get('normalized_name')}: {it.get('quantity')} {it.get('unit')} ({it.get('category')})")
            if parsed.get("clarification_prompt"):
                print(f"    Clarification Prompt: {parsed.get('clarification_prompt')}")
            success_count += 1
        except Exception as exc:
            print(f"[x] Failed: {exc}")

    print(f"\n==========================================")
    print(f"Live Groq Test Results: {success_count}/{len(test_cases)} Passed")
    print(f"==========================================")
    return success_count == len(test_cases)


if __name__ == "__main__":
    passed = asyncio.run(run_live_tests())
    sys.exit(0 if passed else 1)
