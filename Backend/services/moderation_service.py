# Backend/services/moderation_service.py
from __future__ import annotations

from pathlib import Path
from typing import Tuple, Optional

from app.models.ai import ContentModerationResult, ModerationDecision
from app.config import settings

# --- Imports met fallback zodat zowel `services.*` als `app.services.*` werken ---
try:
    from services.openai_service import OpenAIService
    _HAVE_OPENAI = True
except (ImportError, ModuleNotFoundError):
    try:
        from app.services.openai_service import OpenAIService  # type: ignore
        _HAVE_OPENAI = True
    except (ImportError, ModuleNotFoundError):
        OpenAIService = None  # type: ignore
        _HAVE_OPENAI = False
except Exception as e:
    import sys
    if "pytest" not in sys.modules:
        import logging
        logging.warning(f"Unexpected error importing OpenAIService: {e}")
    OpenAIService = None  # type: ignore
    _HAVE_OPENAI = False

# -----------------------------------------------------------------------------
# Prompt-bestanden relatief t.o.v. deze file
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
MODERATION_SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "moderation_system.txt"


def _load_moderation_prompt() -> str:
    """Load the system prompt for content moderation."""
    if MODERATION_SYSTEM_PROMPT_PATH.exists():
        return MODERATION_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    
    # Fallback prompt
    return """Je bent een content moderator voor het Turkish Diaspora App advertentiebord.
Je beoordeelt advertenties op:
1. Aanstootgevende/inappropriate content
2. Spam of misleidende advertenties
3. Illegale activiteiten
4. Categorie correctheid
5. Relevantie voor de Turkish diaspora gemeenschap in Nederland

Antwoord met JSON volgens het schema:
- decision: "approved", "rejected", of "requires_review"
- confidence_score: 0.0-1.0
- reason: specifieke reden
- details: korte uitleg
- flags: lijst van gevonden issues (optioneel)
- suggested_category: als de categorie verkeerd is (optioneel)"""


class ModerationService:
    """AI-powered content moderation for bulletin posts."""
    
    def __init__(self, model: Optional[str] = None):
        self.model = model or settings.OPENAI_MODEL
        
        if not _HAVE_OPENAI:
            raise RuntimeError(
                "OpenAIService is not available; check dependencies and OPENAI_API_KEY. "
                "ModerationService requires OpenAI to be properly configured for production use."
            )
        
        # Runtime check: verify OpenAIService can actually be instantiated
        try:
            self.ai = OpenAIService(model=self.model)  # type: ignore
        except RuntimeError as e:
            error_msg = str(e)
            if "OPENAI_API_KEY" in error_msg or "ontbreekt" in error_msg:
                raise RuntimeError(
                    f"OpenAI API key is not configured. {error_msg} "
                    "Please set OPENAI_API_KEY environment variable."
                ) from e
            raise
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize OpenAIService: {e}. "
                "Check that the 'openai' package is installed and OPENAI_API_KEY is set correctly."
            ) from e
        
        self.system_prompt = _load_moderation_prompt()
    
    def moderate_post(
        self,
        title: str,
        description: Optional[str],
        category: str,
        city: Optional[str] = None,
    ) -> Tuple[ContentModerationResult, dict]:
        """
        Moderate a bulletin post before approval.
        
        Returns:
            (moderation_result, meta_dict)
        """
        user_prompt = self._build_moderation_prompt(
            title=title,
            description=description,
            category=category,
            city=city,
        )
        
        # Call OpenAI service with structured output
        result, meta = self.ai.generate_json(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            response_model=ContentModerationResult,
            action_type="bulletin_moderation",
            location_id=None,
        )
        
        return result, meta
    
    def _build_moderation_prompt(
        self,
        title: str,
        description: Optional[str],
        category: str,
        city: Optional[str],
    ) -> str:
        """Build user prompt for moderation."""
        parts = [
            f"Titel: {title}",
            f"Categorie: {category}",
        ]
        
        if description:
            parts.append(f"Beschrijving: {description}")
        else:
            parts.append("Beschrijving: (geen beschrijving)")
        
        if city:
            parts.append(f"Stad: {city}")
        
        parts.append("\nBeoordeel deze advertentie volgens de moderation richtlijnen.")
        return "\n".join(parts)


# Singleton instance
_moderation_service: Optional[ModerationService] = None


def get_moderation_service() -> ModerationService:
    """Get singleton ModerationService instance."""
    global _moderation_service
    if _moderation_service is None:
        _moderation_service = ModerationService()
    return _moderation_service

