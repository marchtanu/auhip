"""
tests/test_tts.py
-----------------
Standalone test for the TextToSpeech engine and text sanitization.
Validates:
  1. clean_text_for_speech() handles markdown, code blocks, URLs, and emojis.
  2. Edge-TTS neural speech synthesis and sounddevice playback.
  3. pyttsx3 offline fallback speech synthesis.

Run:
    python tests/test_tts.py
"""

import asyncio
import sys
import os
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


from auhip.audio.tts import TextToSpeech, clean_text_for_speech



def test_sanitizer():
    print("\n--- 1. Testing Text Sanitizer ---")
    sample_text = """
    # Weather Report 🌤️
    Here is the **current** forecast for *Tokyo*:
    - Temperature: 18°C 🌡️
    - Conditions: Partly cloudy
    Check out [Weather Site](https://wttr.in/Tokyo) for more details!

    ```python
    def get_temp():
        return 18
    ```
    Have a nice day! 🚀
    """

    cleaned = clean_text_for_speech(sample_text)
    print("Original length:", len(sample_text))
    print("Cleaned length:", len(cleaned))
    print("Cleaned result:\n", cleaned)

    assert "🌤️" not in cleaned, "Emoji was not stripped!"
    assert "https://" not in cleaned, "URL was not stripped!"
    assert "def get_temp" not in cleaned, "Code block was not converted!"
    assert "**" not in cleaned, "Markdown bold asterisks not stripped!"
    print("Sanitizer test: [PASSED]")


async def test_synthesis():
    print("\n--- 2. Testing Edge-TTS Neural Synthesis ---")
    tts = TextToSpeech()
    # Test speaking a short Jarvis phrase
    phrase = "Voice system online. All diagnostic checks passed, sir."
    print(f"Speaking: '{phrase}' using voice: '{tts.voice}'...")
    success = await tts.speak(phrase, block=True)
    print(f"Edge-TTS result: {success}")

    print("\n--- 3. Testing Offline Fallback (pyttsx3) ---")
    tts.set_engine("pyttsx3")
    phrase_offline = "Testing offline speech fallback."
    print(f"Speaking offline: '{phrase_offline}'...")
    success_offline = await tts.speak(phrase_offline, block=True)
    print(f"pyttsx3 result: {success_offline}")

    print("\n--- 4. Testing Mute Control ---")
    tts.set_muted(True)
    assert tts.is_muted is True
    muted_result = await tts.speak("This should not be heard.")
    assert muted_result is False, "Muted TTS should return False!"
    tts.set_muted(False)
    print("Mute test: [PASSED]")


if __name__ == "__main__":
    test_sanitizer()
    asyncio.run(test_synthesis())
    print("\n=== All TTS tests completed successfully! ===")
