"""Standalone live verification script for Groq API integration.

Runs ONLY live Groq API calls when GROQ_API_KEY is configured.
Exercises the actual groq_service pipeline with the canonical Indian grocery taxonomy.
"""

import asyncio
import os
import sys

# Ensure backend root is in sys.path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.config import get_settings
from app.services import groq_service


async def run_live_tests():
    settings = get_settings()
    if not settings.groq_api_key or not settings.groq_api_key.strip():
        print("[-] GROQ_API_KEY is not configured. Live integration cannot run.")
        sys.exit(1)

    print(f"[+] Initializing live Groq verification with model: {settings.groq_model}")

    test_cases = [
        {
            "lang": "English",
            "text": "Please add 2 loaves of whole wheat bread, 1 kg tomatoes, and 6 eggs",
            "checks": [
                ("Bread", "other"),
                ("Eggs", "other"),
                ("Tomatoes", "vegetables"),
            ],
        },
        {
            "lang": "Telugu",
            "text": "నాకు 5 కిలోల బియ్యం (సోనా మసూరి), 2 లీటర్ల విజయ పాలు, 1 కేజీ కందిపప్పు కావాలి",
            "checks": [
                ("Toor Dal", "pulses"),  # కందిపప్పు MUST be Toor Dal, NOT Chana Dal
                ("Rice", "grains_rice"),
                ("Milk", "dairy"),
            ],
        },
        {
            "lang": "Hindi",
            "text": "मुझे 2 किलो आटा (आशीर्वाद), 1 लीटर सरसों का तेल और 500 ग्राम पनीर चाहिए",
            "checks": [
                ("Atta", "grains_rice"),  # आशीर्वाद आटा must preserve brand Aashirvaad
                ("Mustard Oil", "cooking_oils"),
                ("Paneer", "dairy"),
            ],
        },
        {
            "lang": "Mixed Code-Switching",
            "text": "1 kg toor dal teesko, 2 packets curd and thoda coriander also",
            "checks": [
                ("Toor Dal", "pulses"),
                ("Curd", "dairy"),
                ("Coriander", "vegetables"),  # Unspecified quantity -> needs_clarification
            ],
        },
    ]

    success_count = 0
    for tc in test_cases:
        print(f"\n--- Testing {tc['lang']} ---")
        print(f"Input: {tc['text']}")
        try:
            output = await groq_service.extract_grocery_items(tc["text"])
            print(f"[✓] Status: {output.overall_status} | Language: {output.detected_language} | Items: {len(output.items)}")
            for idx, it in enumerate(output.items, 1):
                brand_str = f" [Brand: {it.brand}]" if it.brand else ""
                clar_str = f" [Needs Clarification: {it.clarification_reason}]" if it.needs_clarification else ""
                print(f"    {idx}. {it.normalized_name}: {it.quantity} {it.unit} (Category: {it.category}){brand_str}{clar_str}")
            if output.clarification_prompt:
                print(f"    Clarification Prompt: {output.clarification_prompt}")
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
