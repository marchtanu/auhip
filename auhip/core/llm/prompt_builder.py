import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Centralized prompt assembly engine. Loads core executive rules from user/identity.md
    and binds active machine operational state directly into context headers.
    """

    # Class-level cache to avoid redundant disk reads on every command
    _cached_identity: Optional[str] = None
    _cache_timestamp: float = 0.0
    _CACHE_TTL_SECONDS: float = 60.0

    @staticmethod
    def load_identity() -> str:
        """Loads master instruction sets from persistent identity specification profile.

        Uses a 60-second TTL cache to avoid hitting disk on every voice command.
        """
        now = time.time()
        if (
            PromptBuilder._cached_identity is not None
            and (now - PromptBuilder._cache_timestamp) < PromptBuilder._CACHE_TTL_SECONDS
        ):
            return PromptBuilder._cached_identity

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        identity_path = os.path.join(project_root, "user", "identity.md")
        context_path = os.path.join(project_root, ".agents", "context.md")
        
        combined_text = ""
        try:
            if os.path.exists(context_path):
                with open(context_path, "r", encoding="utf-8") as f:
                    combined_text += f"=== PROJECT ARCHITECTURE CONTEXT ===\n{f.read().strip()}\n\n"
        except Exception as e:
            logger.warning(f"Failed to read secondary context file: {e}")

        try:
            with open(identity_path, "r", encoding="utf-8") as f:
                combined_text += f"=== CORE IDENTITY PROFILE ===\n{f.read().strip()}"
            logger.debug("Successfully resolved primary persistent identity prompt profiles.")
        except Exception as e:
            logger.error(f"Failed to resolve primary identity files: {e}")
            combined_text = combined_text or "You are AUHIP, an executive local-first operating system assistant."

        PromptBuilder._cached_identity = combined_text
        PromptBuilder._cache_timestamp = now
        return combined_text

    @staticmethod
    def build_system_prompt(current_mode: str = "VOICE_MODE") -> str:
        """
        Combines baseline instructions alongside immediate execution state flags
        to instruct models cleanly.
        """
        identity_text = PromptBuilder.load_identity()
        
        mode_header = f"=== CURRENT EXECUTION STATE: {current_mode} ===\n"
        return f"{identity_text}\n\n{mode_header}"

