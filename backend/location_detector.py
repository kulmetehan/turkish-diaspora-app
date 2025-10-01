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


def detect_cities(title: str, summary: str) -> List[str]:
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
    is_likely_dutch = dutch_word_count >= 3
    
    # Track cities we find
    found_cities: Set[str] = set()
    
    # Look for each city name
    for city in ALL_CITIES:
        # Skip 'Van' entirely for Dutch text to avoid false positives
        if city == 'Van' and is_likely_dutch:
            continue
            
        # Create a pattern that matches the city name as a whole word
        # \b means "word boundary" so we don't match partial words
        pattern = r'\b' + re.escape(normalize_text(city)) + r'\b'
        
        # Search for the city name (case-insensitive)
        if re.search(pattern, normalized_text, re.IGNORECASE):
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


# Test function - you can run this file directly to test
if __name__ == "__main__":
    # Test examples
    test_cases = [
        {
            "title": "Amsterdam plans new housing development",
            "summary": "The city of Amsterdam announced plans for 5000 new homes in collaboration with Rotterdam."
        },
        {
            "title": "Istanbul'da trafik sorunu büyüyor",
            "summary": "Istanbul ve Ankara'da trafik yoğunluğu artmaya devam ediyor."
        },
        {
            "title": "Dutch economy grows",
            "summary": "Economic growth reported across the Netherlands including Utrecht and Eindhoven."
        }
    ]
    
    print("\n" + "="*60)
    print("LOCATION DETECTOR TEST")
    print("="*60)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Title: {test['title']}")
        print(f"Summary: {test['summary'][:50]}...")
        
        cities = detect_cities(test['title'], test['summary'])
        print(f"\nDetected cities: {cities}")
        
        if cities:
            for city in cities:
                region = get_city_region(city)
                print(f"  • {city} ({region})")