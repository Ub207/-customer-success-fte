"""
Quick test — agent ko seedha chalaao, Kafka/DB ka wait nahi.
Gemini API key use karega jo .env mein hai.
"""
import asyncio, os, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "production" / ".env")

from openai import AsyncOpenAI

# Provider priority: Groq → Gemini → OpenAI
GROQ_KEY   = os.getenv("GROQ_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

if GROQ_KEY and not GROQ_KEY.startswith("APNI"):
    print("Provider: Groq (llama-3.3-70b) — FREE")
    client = AsyncOpenAI(
        api_key=GROQ_KEY,
        base_url="https://api.groq.com/openai/v1",
        timeout=60.0,
        max_retries=2,
    )
    MODEL  = "llama-3.3-70b-versatile"
elif GEMINI_KEY and not GEMINI_KEY.startswith("APNI"):
    print("Provider: Google Gemini (gemini-1.5-flash) — FREE")
    client = AsyncOpenAI(api_key=GEMINI_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
    MODEL  = "gemini-1.5-flash"
elif OPENAI_KEY and not OPENAI_KEY.startswith("sk-placeholder"):
    print("Provider: OpenAI (gpt-4o)")
    client = AsyncOpenAI(api_key=OPENAI_KEY)
    MODEL  = "gpt-4o"
else:
    print("\nERROR: Koi valid API key nahi mili!")
    print("      1. console.groq.com pe FREE account banao")
    print("      2. API key copy karo")
    print("      3. production/.env mein GROQ_API_KEY=gsk_xxxx daalo")
    sys.exit(1)

SYSTEM = """You are a Customer Success AI agent for TechCorp SaaS.
Answer customer questions helpfully and concisely.
If asked about pricing, refunds, or legal matters — say you will escalate to a human.
Respond in the same language the customer uses."""

async def ask(message: str, channel: str = "web_form"):
    print(f"\n{'='*55}")
    print(f"Channel : {channel}")
    print(f"Message : {message}")
    print(f"{'='*55}")
    print("AI Agent response:\n")

    # Non-streaming — more reliable on slow connections
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": message},
        ],
        max_tokens=500,
    )
    print(response.choices[0].message.content)
    print()

async def main():
    # Subah wala message reproduce karo
    print("\n TechCorp AI Agent — Direct Test")
    print(" (Kafka/DB bypass — seedha Gemini se jawab)\n")

    if len(sys.argv) > 1:
        # Command line se message dena
        msg = " ".join(sys.argv[1:])
        await ask(msg)
    else:
        # Interactive mode
        print("Apna message likho (Enter dabao):")
        print("Chhorne k liye Ctrl+C dabao\n")
        while True:
            try:
                msg = input("Tum: ").strip()
                if not msg:
                    continue
                await ask(msg)
            except (KeyboardInterrupt, EOFError):
                print("\nBye!")
                break

asyncio.run(main())
