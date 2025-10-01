import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def normalize_summary(summary: str, max_words: int = 70) -> str:
    """
    If RSS summary is too long, trim it intelligently.
    If it's already good length, return as-is.
    """
    words = summary.split()
    
    # If already good length, don't process
    if 40 <= len(words) <= max_words:
        return summary
    
    # Too short - return as is (some RSS feeds are minimal)
    if len(words) < 40:
        return summary
    
    # Too long - ask AI to trim intelligently
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You trim text to exactly 70 words while keeping the most important information. Maintain the original language."},
                    {"role": "user", "content": f"Trim this to 70 words:\n\n{summary}"}
                ],
                max_tokens=150,
                temperature=0.3
            )
            
            trimmed = response.choices[0].message.content.strip()
            print(f"  ✂️ Trimmed summary: {len(words)} → {len(trimmed.split())} words")
            return trimmed
            
        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  ⏳ Rate limit, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"  ⚠️ Error trimming: {e}")
                return ' '.join(words[:max_words]) + "..."
    
    # Fallback if all retries failed
    return ' '.join(words[:max_words]) + "..."


def rate_relevance(title: str, summary: str, language: str) -> int:
    """
    Rate article relevance for Turkish diaspora in Netherlands (0-10).
    Higher score = more relevant.
    """
    
    language_name = "Dutch" if language == "nl" else "Turkish"
    
    prompt = f"""Rate this {language_name} article's relevance to Turkish diaspora living in Netherlands.

Consider:
- Cultural relevance to Turkish community
- Practical importance for daily life in Netherlands
- Local impact (Dutch cities, Turkish communities)
- Immigration/integration topics
- Economic opportunities

Return ONLY a number from 0 to 10.
0 = Not relevant
10 = Highly relevant

Title: {title}
Summary: {summary}"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.3
            )
            
            score_text = response.choices[0].message.content.strip()
            score = int(score_text)
            score = max(0, min(10, score))  # Ensure 0-10 range
            
            print(f"  📊 Relevance: {score}/10")
            return score
            
        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  ⏳ Rate limit, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"  ⚠️ Error rating: {e}")
                return 5  # Neutral default
    
    return 5  # Fallback


def extract_topics(title: str, summary: str) -> list:
    """
    Extract 1-3 topic categories from article.
    """
    
    prompt = f"""Categorize this article. Return ONLY a comma-separated list.

Choose 1-3 most relevant from these categories:
Politics, Economy, Sports, Culture, Technology, Health, Crime, Weather, Education, Immigration, Transportation, Housing, Energy, Environment

Title: {title}
Summary: {summary}

Example response: Politics, Immigration
Example response: Sports
Example response: Economy, Housing, Energy"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.3
            )
            
            topics_text = response.choices[0].message.content.strip()
            topics = [t.strip() for t in topics_text.split(',') if t.strip()]
            topics = topics[:3]  # Max 3 topics
            
            print(f"  🏷️ Topics: {', '.join(topics)}")
            return topics
            
        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  ⏳ Rate limit, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"  ⚠️ Error extracting topics: {e}")
                return ["General"]
    
    return ["General"]  # Fallback


def curate_article(title: str, summary: str, language: str) -> dict:
    """
    Complete curation: normalize, rate, and categorize an article.
    
    Returns dict with:
    - summary: normalized summary
    - relevance_score: 0-10 rating
    - category_tags: list of topics
    """
    
    print(f"\n🤖 Curating: {title[:60]}...")
    
    result = {
        'summary': normalize_summary(summary),
        'relevance_score': rate_relevance(title, summary, language),
        'category_tags': extract_topics(title, summary)
    }
    
    return result