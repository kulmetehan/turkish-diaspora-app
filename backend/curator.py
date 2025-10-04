import os
import time
import json
from openai import OpenAI
from dotenv import load_dotenv
from location_detector import detect_cities

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def curate_and_translate_batch(title: str, summary: str, language: str) -> dict:
    """
    Batch process: normalize, rate relevance, extract topics, and translate in ONE API call.
    
    Args:
        title: Article title
        summary: Article summary
        language: Source language ('nl' or 'tr')
    
    Returns:
        dict with all processed data
    """
    
    # Determine target language for translation
    target_language = 'tr' if language == 'nl' else 'nl'
    language_names = {
        'nl': 'Dutch',
        'tr': 'Turkish'
    }
    
    from_lang_name = language_names[language]
    to_lang_name = language_names[target_language]
    
    print(f"\n🤖 Batch AI Processing: {title[:60]}...")
    print(f"   📝 From {from_lang_name} to {to_lang_name}")
    
    # FIXED: Changed from 70 words to 150 characters for consistent UI display
    prompt = f"""Process this {from_lang_name} news article for Turkish diaspora audience:

TITLE: {title}
SUMMARY: {summary}

Please perform ALL these tasks in one go:

1. SUMMARY TRIMMING: Create a summary of EXACTLY 150 characters (not words). 
   - Must be exactly 150 characters including spaces
   - Must be complete sentence(s)
   - Capture the core news event
   - Keep it factual and informative

2. RELEVANCE RATING: Rate relevance to Turkish diaspora in Netherlands (0-10). Consider:
   - Cultural relevance to Turkish community
   - Practical importance for daily life in Netherlands  
   - Local impact (Dutch/Turkish cities, communities)
   - Immigration/integration topics
   - Economic opportunities

3. TOPIC EXTRACTION: Extract 1-3 topics from: Politics, Economy, Sports, Culture, Technology, Health, Crime, Weather, Education, Immigration, Transportation, Housing, Energy, Environment

4. TRANSLATION: Translate title and summary to {to_lang_name}. Maintain factual accuracy and natural phrasing.

Return ONLY valid JSON in this exact format:
{{
  "summary": "exactly 150 character summary",
  "relevance_score": 7,
  "category_tags": ["Politics", "Immigration"],
  "translated_title": "translated title",
  "translated_summary": "translated summary (also 150 chars)"
}}"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a news curator and translator. Always return valid JSON format. Summaries must be exactly 150 characters."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            batch_result = json.loads(result_text)
            
            # Validate and ensure all required fields
            if not batch_result.get('summary'):
                batch_result['summary'] = summary[:147] + "..." if len(summary) > 150 else summary
            if not batch_result.get('relevance_score'):
                batch_result['relevance_score'] = 5
            if not batch_result.get('category_tags'):
                batch_result['category_tags'] = ["General"]
            if not batch_result.get('translated_title'):
                batch_result['translated_title'] = title
            if not batch_result.get('translated_summary'):
                batch_result['translated_summary'] = batch_result.get('summary', summary)[:147] + "..."
            
            # CRITICAL: Enforce 150 character limit on both summaries
            if len(batch_result['summary']) > 150:
                batch_result['summary'] = batch_result['summary'][:147] + "..."
            if len(batch_result['translated_summary']) > 150:
                batch_result['translated_summary'] = batch_result['translated_summary'][:147] + "..."
            
            # Ensure relevance score is within bounds
            batch_result['relevance_score'] = max(0, min(10, int(batch_result['relevance_score'])))
            
            print(f"  📊 Relevance: {batch_result['relevance_score']}/10")
            print(f"  🏷️ Topics: {', '.join(batch_result['category_tags'])}")
            print(f"  🌐 Translation: {batch_result['translated_title'][:50]}...")
            
            # Add the target language
            batch_result['translated_language'] = target_language
            
            return batch_result
            
        except json.JSONDecodeError as e:
            print(f"  ⚠️ JSON parsing error: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  ⏳ Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"  ❌ Failed to parse JSON after {max_retries} attempts")
                return create_fallback_result(title, summary, language, target_language)
                
        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  ⏳ Rate limit, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"  ⚠️ Batch processing error: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"  ⏳ Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    return create_fallback_result(title, summary, language, target_language)
    
    return create_fallback_result(title, summary, language, target_language)


def create_fallback_result(title: str, summary: str, language: str, target_language: str) -> dict:
    """
    Create a fallback result when batch processing fails
    Ensures 150 character limit is enforced
    """
    print("  ⚠️ Using fallback processing")
    
    # Simple character-based trimming as fallback (not word-based)
    if len(summary) > 150:
        trimmed_summary = summary[:147] + '...'
    else:
        # Pad if too short for consistency
        trimmed_summary = summary
    
    return {
        'summary': trimmed_summary,
        'relevance_score': 5,
        'category_tags': ['General'],
        'translated_title': title,
        'translated_summary': trimmed_summary,
        'translated_language': target_language
    }


def tag_locations(title: str, summary: str, language: str) -> list:
    """Detect and tag cities mentioned in content
    
    Args:
        title: Article title
        summary: Article summary
        language: Article language ('nl' or 'tr')
        
    Returns:
        List of city names found
    """
    try:
        print("  📍 Detecting locations...")
        
        # Regular city detection
        cities = detect_cities(title, summary)
        
        # If no cities detected, tag with capital city as fallback
        if not cities:
            if language == 'tr':
                cities = ['Ankara']
            else:
                cities = ['Den Haag']
        
        if cities:
            print(f"  ✓ Tagged {len(cities)} locations: {', '.join(cities)}")
        else:
            print("  ℹ️ No locations detected")
            
        return cities
        
    except Exception as e:
        print(f"  ❌ Location detection error: {e}")
        return []


# Legacy functions kept for backwards compatibility
def normalize_summary(text, target_length=150):
    """Legacy function - not used in current pipeline"""
    return text[:147] + "..." if len(text) > 150 else text


def rate_relevance(title: str, summary: str, language: str) -> int:
    """Legacy function - kept for compatibility"""
    return 5


def extract_topics(title: str, summary: str) -> list:
    """Legacy function - kept for compatibility"""
    return ["General"]


def curate_article(title: str, summary: str, language: str) -> dict:
    """Legacy function - kept for compatibility"""
    print(f"\n🤖 Curating: {title[:60]}...")
    
    # Use batch processing internally for legacy calls
    batch_result = curate_and_translate_batch(title, summary, language)
    
    return {
        'summary': batch_result['summary'],
        'relevance_score': batch_result['relevance_score'],
        'category_tags': batch_result['category_tags']
    }


def translate_content(title: str, summary: str, from_language: str) -> dict:
    """Legacy function - kept for compatibility"""
    print(f"\n🌐 Translating from {from_language}...")
    
    # Use batch processing internally for legacy calls
    batch_result = curate_and_translate_batch(title, summary, from_language)
    
    return {
        'translated_title': batch_result['translated_title'],
        'translated_summary': batch_result['translated_summary'],
        'translated_language': batch_result['translated_language']
    }