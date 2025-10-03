"""
Location Detection System for Turkish Diaspora App
Identifies and tags Turkish and Dutch cities mentioned in content
"""

import re
from typing import List, Set
import logging

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Major Turkish cities to detect
TURKISH_CITIES = {
    'Istanbul', 'Ankara', 'İzmir', 'Bursa', 'Antalya', 
    'Adana', 'Gaziantep', 'Konya', 'Kayseri', 'Diyarbakır',
    'Mersin', 'Eskişehir', 'Samsun', 'Denizli', 'Trabzon',
    'Balıkesir', 'Kahramanmaraş', 'Van', 'Erzurum', 'Elazığ',
    'Malatya', 'Manisa', 'Sivas', 'Tekirdağ', 'Kocaeli',
    'Hatay', 'Şanlıurfa', 'Aydın', 'Sakarya', 'Muğla',
    'Isparta', 'Afyonkarahisar', 'Ordu', 'Kütahya', 'Zonguldak'
}

# Major Dutch cities to detect
DUTCH_CITIES = {
    'Amsterdam', 'Rotterdam', 'Den Haag', 'Utrecht', 'Eindhoven',
    'Groningen', 'Tilburg', 'Almere', 'Breda', 'Nijmegen',
    'Enschede', 'Haarlem', 'Arnhem', 'Zaanstad', 'Amersfoort',
    'Apeldoorn', 'Den Bosch', "'s-Hertogenbosch", 'Hoofddorp', 
    'Maastricht', 'Leiden', 'Dordrecht', 'Zoetermeer', 'Zwolle',
    'Deventer', 'Delft', 'Alkmaar', 'Heerlen', 'Venlo',
    'The Hague', 'Vlaardingen', 'Schiedam', 'Capelle aan den IJssel'
}

# Combine all cities for detection
ALL_CITIES = TURKISH_CITIES | DUTCH_CITIES

# Common words that might be mistaken for cities
FALSE_POSITIVES = {
    'van', 'der', 'den', 'het', 'de', 'een', 'op', 'in', 'uit',
    'aan', 'te', 'bij', 'door', 'voor', 'naar', 'met', 'als'
}


def normalize_text(text: str) -> str:
    """
    Clean up text for better city detection
    
    Args:
        text: The text to normalize
        
    Returns:
        Cleaned text ready for city detection
    """
    if not text:
        return ""
    
    # Replace common Turkish character variations
    text = text.replace('ı', 'i').replace('İ', 'I')
    text = text.replace('ğ', 'g').replace('Ğ', 'G')
    text = text.replace('ü', 'u').replace('Ü', 'U')
    text = text.replace('ş', 's').replace('Ş', 'S')
    text = text.replace('ö', 'o').replace('Ö', 'O')
    text = text.replace('ç', 'c').replace('Ç', 'C')
    
    return text


def detect_cities(title: str, summary: str, language: str = None) -> List[str]:
    """
    Find all city names mentioned in the article
    
    Args:
        title: Article title
        summary: Article summary/content
        
    Returns:
        List of city names found (e.g., ['Amsterdam', 'Istanbul'])
    """
    # Combine title and summary for searching
    full_text = f"{title} {summary}"
    
    # If text is empty, return empty list
    if not full_text or full_text.strip() == "":
        return []
    
    # Clean up the text
    normalized_text = normalize_text(full_text)
    
    # Check if this appears to be Dutch text
    # Common Dutch words that don't appear in Turkish
    dutch_indicators = ['de', 'het', 'een', 'en', 'van', 'voor', 'in', 'op', 'met']
    text_lower = normalized_text.lower()
    dutch_word_count = sum(1 for word in dutch_indicators if f' {word} ' in f' {text_lower} ')
    is_likely_dutch = dutch_word_count >= 2
    
    # Check if this appears to be Turkish text
    turkish_indicators = ['ve', 'bir', 'bu', 'ile', 'için', 'gibi', 'kadar', 'sonra']
    turkish_word_count = sum(1 for word in turkish_indicators if f' {word} ' in f' {text_lower} ')
    is_likely_turkish = turkish_word_count >= 2
    
    # Track cities we find
    found_cities: Set[str] = set()
    
    # Look for each city name
    for city in ALL_CITIES:
        # Skip problematic cities based on context
        if city == 'Van' and is_likely_dutch:
            continue  # Skip Van in Dutch text to avoid false positives
            
        # Create a pattern that matches the city name as a whole word
        # \b means "word boundary" so we don't match partial words
        pattern = r'\b' + re.escape(normalize_text(city)) + r'\b'
        
        # Search for the city name (case-insensitive)
        if re.search(pattern, normalized_text, re.IGNORECASE):
            # Additional validation for common false positives
            if city.lower() in FALSE_POSITIVES:
                # Check if it's actually used as a city name (capitalized, in specific contexts)
                city_pattern = r'(?:in|uit|naar|van)\s+' + re.escape(normalize_text(city))
                if not re.search(city_pattern, normalized_text, re.IGNORECASE):
                    continue
                    
            found_cities.add(city)
            logger.info(f"✓ Found city: {city}")
    
    # Convert set to sorted list for consistent ordering
    result = sorted(list(found_cities))
    
    if result:
        logger.info(f"📍 Total cities detected: {len(result)} - {', '.join(result)}")
    else:
        logger.info("📍 No cities detected in this content")
    
    return result


def get_city_region(city: str) -> str:
    """
    Determine if a city is Turkish or Dutch
    
    Args:
        city: City name
        
    Returns:
        Either 'Turkey' or 'Netherlands'
    """
    if city in TURKISH_CITIES:
        return 'Turkey'
    elif city in DUTCH_CITIES:
        return 'Netherlands'
    else:
        return 'Unknown'


def detect_national_news(title: str, summary: str, language: str) -> List[str]:
    """
    Detect national-level news and assign appropriate capital city
    
    Args:
        title: Article title
        summary: Article summary
        language: Language code ('nl' or 'tr')
        
    Returns:
        List with capital city if this appears to be national news
    """
    # National-level keywords that indicate country-wide relevance
    national_keywords_nl = {
        'nederland', 'landelijk', 'rijksoverheid', 'regering', 'premier', 
        'kabinet', 'tweede kamer', 'minister', 'national', 'heel nederland'
    }
    
    national_keywords_tr = {
        'türkiye', 'ülke', 'milli', 'hükümet', 'cumhurbaşkanı', 'başbakan',
        'bakan', 'meclis', 'ulusal', 'genel', 'tüm türkiye'
    }
    
    full_text = f"{title} {summary}".lower()
    
    if language == 'nl':
        keywords = national_keywords_nl
        capital = 'Den Haag'
    else:
        keywords = national_keywords_tr
        capital = 'Ankara'
    
    # Check for national-level keywords
    national_keyword_count = sum(1 for keyword in keywords if keyword in full_text)
    
    # If we find multiple national keywords, it's likely national news
    if national_keyword_count >= 2:
        logger.info(f"🇳🇱 National news detected, assigning capital: {capital}")
        return [capital]
    
    return []


# Test function - you can run this file directly to test
if __name__ == "__main__":
    # Test examples
    test_cases = [
        {
            "title": "Amsterdam plans new housing development",
            "summary": "The city of Amsterdam announced plans for 5000 new homes in collaboration with Rotterdam.",
            "language": "nl"
        },
        {
            "title": "Istanbul'da trafik sorunu büyüyor",
            "summary": "Istanbul ve Ankara'da trafik yoğunluğu artmaya devam ediyor.",
            "language": "tr"
        },
        {
            "title": "Dutch economy grows",
            "summary": "Economic growth reported across the Netherlands including Utrecht and Eindhoven.",
            "language": "nl"
        },
        {
            "title": "Van uit Amsterdam naar Rotterdam",
            "summary": "Reis van Amsterdam naar Rotterdam was snel",
            "language": "nl"
        }
    ]
    
    print("\n" + "="*60)
    print("LOCATION DETECTOR TEST")
    print("="*60)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Title: {test['title']}")
        print(f"Summary: {test['summary'][:50]}...")
        print(f"Language: {test['language']}")
        
        cities = detect_cities(test['title'], test['summary'])
        national_cities = detect_national_news(test['title'], test['summary'], test['language'])
        
        all_cities = list(set(cities + national_cities))
        
        print(f"\nDetected cities: {all_cities}")
        
        if all_cities:
            for city in all_cities:
                region = get_city_region(city)
                print(f"  • {city} ({region})")