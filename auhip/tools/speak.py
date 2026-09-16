"""
CLI Bridge for AUHIP Text-To-Speech.
Allows Antigravity, shell scripts, or background processes to speak through AUHIP's neural voice engine.

Usage:
    python -m auhip.tools.speak "Task completed successfully."
"""

import sys
import asyncio
from auhip.audio.tts import TextToSpeech


async def main():
    if len(sys.argv) < 2:
        print("Usage: python -m auhip.tools.speak \"Text to speak\"")
        return
    
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        return

    tts = TextToSpeech()
    success = await tts.speak(text, block=True)
    if success:
        print(f"[AUHIP Voice] Spoke: {text}")
    else:
        print("[AUHIP Voice] Muted or speech cancelled.")


if __name__ == "__main__":
    asyncio.run(main())
