"""
Helper function to generate human-readable explanations from AI log records.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.models.ai import (
    AIClassification,
    AIVerificationResult,
    TA_CLASSIFICATION,
    TA_VERIFICATION,
    Action,
    VerificationStatus,
)
from services.ai_validation import (
    validate_classification_payload,
    validate_verification_payload,
)


def generate_ai_explanation(ai_log_record: Dict[str, Any]) -> str:
    """
    Generate a human-readable explanation from an AI log record.
    
    Args:
        ai_log_record: Dictionary containing ai_logs row data, including:
            - validated_output: JSONB field with parsed AI response
            - action_type: Type of action (e.g., 'classify', 'verify_locations.classified')
            - is_success: Whether the operation succeeded
            - error_message: Error message if operation failed
    
    Returns:
        Human-readable explanation string
    """
    # Handle error cases first
    is_success = ai_log_record.get("is_success", True)
    error_message = ai_log_record.get("error_message")
    
    if not is_success:
        if error_message:
            return f"Failed: {error_message}"
        return "Failed: Unknown error occurred during AI processing."
    
    validated_output = ai_log_record.get("validated_output")
    action_type = ai_log_record.get("action_type", "")
    
    # Ensure validated_output is a dict (should already be parsed in router, but be defensive)
    if validated_output and isinstance(validated_output, str):
        # This shouldn't happen if router parses correctly, but handle it gracefully
        try:
            parsed = json.loads(validated_output)
            if isinstance(parsed, dict):
                validated_output = parsed
            else:
                validated_output = None
        except Exception:
            validated_output = None
    
    if not validated_output or not isinstance(validated_output, dict):
        return "AI decision recorded (no output data available)."
    
    # Handle admin audit actions (stored in validated_output)
    if action_type.startswith("admin.") or action_type.startswith("admin_"):
        actor = validated_output.get("actor", "admin")
        action = validated_output.get("action", action_type)
        return f"{actor} performed {action}."
    
    # Try to parse as AIClassification
    try:
        # First try using the validation helper (safest)
        classification = validate_classification_payload(validated_output)
        
        category = classification.category.value if classification.category else "unknown category"
        confidence = classification.confidence_score
        
        if classification.action == Action.KEEP:
            reason_part = f" based on {classification.reason}" if classification.reason else " based on name and address"
            return f"Classified as {category} with confidence {confidence:.2f}{reason_part}."
        else:  # Action.IGNORE
            reason_part = f": {classification.reason}" if classification.reason else ""
            return f"Ignored as non-relevant (confidence {confidence:.2f}){reason_part}."
            
    except Exception:
        # Not a classification, try verification
        pass
    
    # Try to parse as AIVerificationResult
    try:
        verification = validate_verification_payload(validated_output)
        
        status = verification.status.value if isinstance(verification.status, VerificationStatus) else str(verification.status)
        reasons = verification.reasons or []
        
        reasons_text = ". ".join(reasons) if reasons else "No specific reasons provided"
        return f"Verification status: {status}. {reasons_text}."
        
    except Exception:
        # Not a verification either
        pass
    
    # Fallback: Try to extract common fields directly from JSON
    if isinstance(validated_output, dict):
        # Check for classification-like structure
        if "action" in validated_output and "confidence_score" in validated_output:
            action = validated_output.get("action", "unknown")
            category = validated_output.get("category", "unknown")
            confidence = validated_output.get("confidence_score", 0.0)
            reason = validated_output.get("reason", "")
            
            if action == "keep":
                reason_part = f" based on {reason}" if reason else ""
                return f"Classified as {category} with confidence {confidence:.2f}{reason_part}."
            else:
                reason_part = f": {reason}" if reason else ""
                return f"Ignored (confidence {confidence:.2f}){reason_part}."
        
        # Check for verification-like structure
        if "status" in validated_output:
            status = validated_output.get("status", "unknown")
            reasons = validated_output.get("reasons", [])
            reasons_text = ". ".join(reasons) if isinstance(reasons, list) else str(reasons)
            return f"Verification status: {status}. {reasons_text}."
        
        # Generic fallback
        return f"AI decision recorded (action_type: {action_type})."
    
    # Ultimate fallback
    return f"AI decision recorded for action '{action_type}'."

