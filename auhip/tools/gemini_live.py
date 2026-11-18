"""Standalone Gemini Live client using the shared, consent-gated audio engine."""

import argparse
import asyncio

from auhip.audio.gemini_live_engine import GeminiLiveEngine
from auhip.audio.microphone import Microphone


class GeminiLiveVoiceClient:
    def __init__(self, voice_name: str = "Puck", device_index: int | None = None,
                 *, accept_audio_sharing: bool = False) -> None:
        self.mic = Microphone()
        self.device_index = device_index
        self.engine = GeminiLiveEngine(
            mic=self.mic, voice_name=voice_name, session_approved=accept_audio_sharing,
        )

    async def run(self) -> None:
        try:
            self.mic.start(self.device_index)
            await self.engine.run()
        finally:
            self.engine.stop()
            self.mic.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="AUHIP Gemini Live voice conversation")
    parser.add_argument("--voice", default="Puck", choices=["Puck", "Charon", "Kore", "Fenrir", "Aoede"])
    parser.add_argument("--device", type=int)
    parser.add_argument(
        "--accept-audio-sharing", action="store_true",
        help="Allow this session's microphone audio and conversation to be sent to Google until stopped.",
    )
    args = parser.parse_args()
    if not args.accept_audio_sharing:
        parser.error("Live audio sharing requires --accept-audio-sharing and CLOUD_ENABLED=true.")
    try:
        client = GeminiLiveVoiceClient(args.voice, args.device, accept_audio_sharing=True)
        asyncio.run(client.run())
    except PermissionError as error:
        parser.error(str(error))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
