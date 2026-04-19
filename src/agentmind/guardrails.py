"""
Guardrails and safety features for AgentMind.

This module provides:
- PII detection and anonymization
- Content filtering
- Rate limiting
- Input validation
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PIIDetection:
    """Result of PII detection."""

    found: bool
    types: List[str]
    locations: List[Dict[str, Any]]
    anonymized_text: Optional[str] = None


class GuardrailsManager:
    """Manages safety and guardrails for AgentMind."""

    def __init__(
        self,
        enable_pii_detection: bool = True,
        enable_content_filtering: bool = True,
        auto_anonymize: bool = False,
    ):
        """Initialize guardrails manager.

        Args:
            enable_pii_detection: Enable PII detection
            enable_content_filtering: Enable content filtering
            auto_anonymize: Automatically anonymize detected PII
        """
        self.enable_pii_detection = enable_pii_detection
        self.enable_content_filtering = enable_content_filtering
        self.auto_anonymize = auto_anonymize

        # PII patterns
        self.pii_patterns = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "url": (
                r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}"
                r"\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)"
            ),
        }

        # Content filtering patterns (basic)
        self.blocked_patterns = [
            r"\b(?:password|passwd|pwd)\s*[:=]\s*\S+",
            r"\b(?:api[_-]?key|apikey)\s*[:=]\s*\S+",
            r"\b(?:secret|token)\s*[:=]\s*\S+",
        ]

    def detect_pii(self, text: str) -> PIIDetection:
        """Detect PII in text.

        Args:
            text: Text to analyze

        Returns:
            PIIDetection result
        """
        if not self.enable_pii_detection:
            return PIIDetection(found=False, types=[], locations=[])

        found_types = []
        locations = []
        anonymized_text = text

        for pii_type, pattern in self.pii_patterns.items():
            matches = list(re.finditer(pattern, text, re.IGNORECASE))

            if matches:
                found_types.append(pii_type)

                for match in matches:
                    locations.append(
                        {
                            "type": pii_type,
                            "start": match.start(),
                            "end": match.end(),
                            "text": match.group(),
                        }
                    )

                    # Anonymize if enabled
                    if self.auto_anonymize:
                        replacement = self._get_replacement(pii_type)
                        anonymized_text = re.sub(
                            pattern, replacement, anonymized_text, flags=re.IGNORECASE
                        )

        return PIIDetection(
            found=len(found_types) > 0,
            types=found_types,
            locations=locations,
            anonymized_text=anonymized_text if self.auto_anonymize else None,
        )

    def _get_replacement(self, pii_type: str) -> str:
        """Get replacement text for PII type."""
        replacements = {
            "email": "[EMAIL]",
            "phone": "[PHONE]",
            "ssn": "[SSN]",
            "credit_card": "[CREDIT_CARD]",
            "ip_address": "[IP_ADDRESS]",
            "url": "[URL]",
        }
        return replacements.get(pii_type, "[REDACTED]")

    def check_content(self, text: str) -> Dict[str, Any]:
        """Check content for blocked patterns.

        Args:
            text: Text to check

        Returns:
            Dictionary with check results
        """
        if not self.enable_content_filtering:
            return {"blocked": False, "reasons": []}

        blocked_reasons = []

        for pattern in self.blocked_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                blocked_reasons.append(f"Matched blocked pattern: {pattern}")

        return {"blocked": len(blocked_reasons) > 0, "reasons": blocked_reasons}

    def validate_input(
        self, text: str, max_length: int = 10000, min_length: int = 1
    ) -> Dict[str, Any]:
        """Validate input text.

        Args:
            text: Text to validate
            max_length: Maximum allowed length
            min_length: Minimum required length

        Returns:
            Dictionary with validation results
        """
        errors = []

        # Check length
        if len(text) < min_length:
            errors.append(f"Text too short (minimum {min_length} characters)")

        if len(text) > max_length:
            errors.append(f"Text too long (maximum {max_length} characters)")

        # Check for null bytes
        if "\x00" in text:
            errors.append("Text contains null bytes")

        # Check for excessive whitespace
        if len(text.strip()) == 0:
            errors.append("Text is empty or contains only whitespace")

        return {"valid": len(errors) == 0, "errors": errors}

    def sanitize_output(self, text: str) -> str:
        """Sanitize output text.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text
        """
        # Remove null bytes
        text = text.replace("\x00", "")

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        # Trim
        text = text.strip()

        return text

    def check_all(self, text: str) -> Dict[str, Any]:
        """Run all guardrail checks.

        Args:
            text: Text to check

        Returns:
            Dictionary with all check results
        """
        results = {"safe": True, "warnings": [], "errors": []}

        # Validate input
        validation = self.validate_input(text)
        if not validation["valid"]:
            results["safe"] = False
            results["errors"].extend(validation["errors"])
            return results

        # Check PII
        pii_detection = self.detect_pii(text)
        if pii_detection.found:
            results["warnings"].append(f"PII detected: {', '.join(pii_detection.types)}")

        # Check content
        content_check = self.check_content(text)
        if content_check["blocked"]:
            results["safe"] = False
            results["errors"].extend(content_check["reasons"])

        return results


# Global guardrails manager instance
_guardrails_manager: Optional[GuardrailsManager] = None


def get_guardrails_manager() -> Optional[GuardrailsManager]:
    """Get the global guardrails manager instance."""
    return _guardrails_manager


def initialize_guardrails(
    enable_pii_detection: bool = True,
    enable_content_filtering: bool = True,
    auto_anonymize: bool = False,
) -> GuardrailsManager:
    """Initialize global guardrails manager.

    Args:
        enable_pii_detection: Enable PII detection
        enable_content_filtering: Enable content filtering
        auto_anonymize: Automatically anonymize detected PII

    Returns:
        GuardrailsManager instance
    """
    global _guardrails_manager

    _guardrails_manager = GuardrailsManager(
        enable_pii_detection=enable_pii_detection,
        enable_content_filtering=enable_content_filtering,
        auto_anonymize=auto_anonymize,
    )

    return _guardrails_manager
