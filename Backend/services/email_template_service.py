# Backend/services/email_template_service.py
"""
Email template service for rendering transactional emails with base templates and multilingual support.

Uses Jinja2 template inheritance to provide consistent branding and structure.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from pathlib import Path
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.logging import get_logger

logger = get_logger()


class EmailTemplateService:
    """
    Service for rendering email templates with base template inheritance and multilingual support.
    """
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize email template service.
        
        Args:
            templates_dir: Directory containing email templates. Defaults to Backend/templates/emails/
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent / "templates" / "emails"
        
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    
    def _get_default_context(self, language: str = "nl") -> Dict[str, Any]:
        """
        Get default context variables for templates.
        
        Args:
            language: Language code (nl, tr, en)
            
        Returns:
            Dictionary with default context variables
            
        Default context variables:
            - language: Language code (nl, tr, en)
            - base_url: Frontend base URL (from FRONTEND_URL env var)
            - unsubscribe_url: URL to account preferences page
            
        Outreach-specific variables (should be provided in context):
            - location_name: Name of the location (string)
            - mapview_link: Link to mapview with focus parameter (string)
            - opt_out_link: Link for opt-out (string, optional)
        """
        frontend_url = os.getenv("FRONTEND_URL", "https://turkspot.nl")
        
        return {
            "language": language,
            "base_url": frontend_url,
            "unsubscribe_url": f"{frontend_url}/#/account",
        }
    
    def render_template(
        self,
        template_name: str,
        context: Optional[Dict[str, Any]] = None,
        language: str = "nl",
    ) -> tuple[str, str]:
        """
        Render an email template with base template inheritance.
        
        Args:
            template_name: Name of template file (without extension)
            context: Additional template variables (merged with defaults)
                For outreach emails, provide: location_name, mapview_link, opt_out_link
            language: Language code (nl, tr, en)
            
        Returns:
            Tuple of (html_body, text_body)
            
        Example usage for outreach email:
            context = {
                "location_name": "Restaurant XYZ",
                "mapview_link": "https://turkspot.nl/#/map?focus=123",
                "opt_out_link": "https://turkspot.nl/#/opt-out?token=abc",
            }
            html, text = service.render_template("outreach_email", context, language="nl")
        """
        # Merge default context with provided context
        default_context = self._get_default_context(language)
        if context:
            default_context.update(context)
        final_context = default_context
        
        html_body = ""
        text_body = ""
        
        # Load and render HTML template
        html_template_path = self.templates_dir / f"{template_name}.html.j2"
        if html_template_path.exists():
            try:
                template = self.env.get_template(f"{template_name}.html.j2")
                html_body = template.render(**final_context)
            except Exception as e:
                logger.error(
                    "template_render_failed",
                    template=template_name,
                    error=str(e),
                    exc_info=True,
                )
                raise
        
        # Load and render text template
        text_template_path = self.templates_dir / f"{template_name}.txt.j2"
        if text_template_path.exists():
            try:
                template = self.env.get_template(f"{template_name}.txt.j2")
                text_body = template.render(**final_context)
            except Exception as e:
                logger.error(
                    "text_template_render_failed",
                    template=template_name,
                    error=str(e),
                    exc_info=True,
                )
                # Fallback to HTML if text template fails
                if not text_body:
                    text_body = html_body
        else:
            # Generate simple text from HTML if no text template exists
            # This is a basic fallback - proper text templates are preferred
            text_body = html_body
        
        return (html_body, text_body)


# Global instance (lazy initialization)
_template_service: Optional[EmailTemplateService] = None


def get_email_template_service() -> EmailTemplateService:
    """Get or create the global email template service instance."""
    global _template_service
    if _template_service is None:
        _template_service = EmailTemplateService()
    return _template_service

