#!/usr/bin/env python3
"""
Production RSS Feed Ingestion for Turkish Diaspora App
Handles real news feeds with proper error handling and SSL fixes
"""

import os
import feedparser
import ssl
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional
import time
import json

# Fix SSL certificate verification on macOS
ssl._create_default_https_context = ssl._create_unverified_context

# Load environment
load_dotenv()

# Initialize Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

class RealNewsIngestion:
    def __init__(self):
        self.stats = {
            'feeds_processed': 0,
            'items_found': 0,
            'items_saved': 0,
            'errors': 0
        }
        
    def clean_text(self, text: str) -> str:
        """Remove HTML tags and clean text"""
        if not text:
            return ""
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:1000]  # Limit length
    
    def extract_summary(self, content: str, title: str = "") -> str:
        """Extract a meaningful summary"""
        clean_content = self.clean_text(content)
        if not clean_content and title:
            return title[:200]
        
        sentences = clean_content.split('.')