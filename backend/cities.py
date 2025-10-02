"""
City definitions for Google News fetching
Based on actual Turkish diaspora population data in Netherlands
and Turkish province origin data

Data sources:
- Dutch cities: CBS Statline via AlleCijfers (2022)
- Turkish provinces: LSO'84, CBS, AOW'10 (1984-2010)
"""

# Dutch cities with significant Turkish diaspora population
# Ranked by number of people of Turkish descent
# Source: CBS Statline (via AlleCijfers) 2022
DUTCH_CITIES = [
    ("Rotterdam", "Zuid-Holland", 47750),
    ("Amsterdam", "Noord-Holland", 44882),
    ("Den Haag", "Zuid-Holland", 42148),
    ("Utrecht", "Utrecht", 14466),
    ("Zaanstad", "Noord-Holland", 12848),
    ("Eindhoven", "Noord-Brabant", 11819),
    ("Enschede", "Overijssel", 8812),
    ("Arnhem", "Gelderland", 8621),
    ("Tilburg", "Noord-Brabant", 8431),
    ("Schiedam", "Zuid-Holland", 8137),
    ("Deventer", "Overijssel", 6819),
    ("Dordrecht", "Zuid-Holland", 6756),
    ("Haarlem", "Noord-Holland", 6720),
    ("Amersfoort", "Utrecht", 6437),
    ("Almelo", "Overijssel", 5774),
    ("Nijmegen", "Gelderland", 5579),
    ("Vlaardingen", "Zuid-Holland", 5273),
    ("Hengelo", "Overijssel", 4771),
    ("Almere", "Flevoland", 4674),
    ("Apeldoorn", "Gelderland", 4540),
    ("Oss", "Noord-Brabant", 4281),
    ("Venlo", "Limburg", 4047),
    ("Haarlemmermeer", "Noord-Holland", 3384),
    ("Breda", "Noord-Brabant", 3286),
    ("Bergen op Zoom", "Noord-Brabant", 3177),
]

# Turkish provinces/cities with highest emigration to Netherlands
# Ranked by estimated number of emigrants to NL
# Sources: LSO'84, CBS, AOW'10
TURKISH_CITIES = [
    ("Konya", 27500),
    ("Kayseri", 17500),
    ("Ankara", 15000),
    ("Yozgat", 13000),
    ("Karaman", 13500),
    ("Kırşehir", 8000),
    ("Niğde", 7000),
    ("Nevşehir", 5000),
    ("Aksaray", 5500),
    ("Adana", 7000),
    ("Sivas", 6000),
    ("Kars", 6000),
    ("Trabzon", 5000),
    ("Samsun", 4000),
    ("Aydın", 5000),
    ("İzmir", 4000),
    ("İstanbul", 6000),
    ("Gaziantep", 4000),
    ("Afyonkarahisar", 5000),
    ("Giresun", 4000),
    ("Denizli", 4000),
    ("Ordu", 3000),
    ("Sakarya", 3000),
    ("Kahramanmaraş", 2500),
    ("Erzincan", 2500),
]


def get_all_cities():
    """
    Return all cities as a list of dicts for easy use in fetcher
    
    Returns:
        List of dicts with city info including name, country, language, etc.
    """
    cities = []
    
    # Add Dutch cities
    for name, province, population in DUTCH_CITIES:
        cities.append({
            'name': name,
            'province': province,
            'population': population,
            'country': 'Netherlands',
            'country_code': 'NL',
            'language': 'nl'
        })
    
    # Add Turkish cities/provinces
    for name, emigrants in TURKISH_CITIES:
        cities.append({
            'name': name,
            'province': name,  # For Turkish, province name = city name
            'population': emigrants,  # Number who emigrated to NL
            'country': 'Turkey',
            'country_code': 'TR',
            'language': 'tr'
        })
    
    return cities


def get_turkish_cities():
    """Return only Turkish cities/provinces"""
    return [c for c in get_all_cities() if c['country'] == 'Turkey']


def get_dutch_cities():
    """Return only Dutch cities"""
    return [c for c in get_all_cities() if c['country'] == 'Netherlands']


def get_city_names_by_country(country_code):
    """
    Get list of city names for a specific country
    
    Args:
        country_code: 'NL' or 'TR'
    
    Returns:
        List of city name strings
    """
    all_cities = get_all_cities()
    return [c['name'] for c in all_cities if c['country_code'] == country_code]


def get_top_cities(country_code, limit=10):
    """
    Get top N cities by population/emigrants
    
    Args:
        country_code: 'NL' or 'TR'
        limit: Number of cities to return
    
    Returns:
        List of city dicts sorted by population
    """
    all_cities = get_all_cities()
    filtered = [c for c in all_cities if c['country_code'] == country_code]
    # Already sorted by population in source data
    return filtered[:limit]


# Quick reference - total counts
TOTAL_DUTCH_CITIES = len(DUTCH_CITIES)  # 25
TOTAL_TURKISH_CITIES = len(TURKISH_CITIES)  # 25
TOTAL_CITIES = TOTAL_DUTCH_CITIES + TOTAL_TURKISH_CITIES  # 50