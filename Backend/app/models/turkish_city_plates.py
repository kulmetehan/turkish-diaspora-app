"""
Mapping of Turkish cities to their license plate numbers (plaka kodları).
Used to display city tags next to usernames.
"""

TURKISH_CITY_PLATE_MAP: dict[str, str] = {
    # Main cities mentioned by user
    "adana": "01",
    "adiyaman": "02",
    "istanbul": "34",
    "trabzon": "61",
    "kirsehir": "40",
    
    # Complete list of Turkish provinces
    "afyonkarahisar": "03",
    "afyon": "03",
    "agri": "04",
    "ağrı": "04",
    "amasya": "05",
    "ankara": "06",
    "antalya": "07",
    "artvin": "08",
    "aydin": "09",
    "aydın": "09",
    "balikesir": "10",
    "balıkesir": "10",
    "bilecik": "11",
    "bingol": "12",
    "bingöl": "12",
    "bitlis": "13",
    "bolu": "14",
    "burdur": "15",
    "bursa": "16",
    "canakkale": "17",
    "çanakkale": "17",
    "cankiri": "18",
    "çankırı": "18",
    "corum": "19",
    "çorum": "19",
    "denizli": "20",
    "diyarbakir": "21",
    "diyarbakır": "21",
    "edirne": "22",
    "elazig": "23",
    "elazığ": "23",
    "erzincan": "24",
    "erzurum": "25",
    "eskisehir": "26",
    "eskişehir": "26",
    "gaziantep": "27",
    "giresun": "28",
    "gumushane": "29",
    "gümüşhane": "29",
    "hakkari": "30",
    "hakkâri": "30",
    "hatay": "31",
    "isparta": "32",
    "mersin": "33",
    "izmir": "35",
    "kars": "36",
    "kastamonu": "37",
    "kayseri": "38",
    "kirklareli": "39",
    "kırklareli": "39",
    "kocaeli": "41",
    "konya": "42",
    "kutahya": "43",
    "kütahya": "43",
    "malatya": "44",
    "manisa": "45",
    "kahramanmaras": "46",
    "kahramanmaraş": "46",
    "mardin": "47",
    "mugla": "48",
    "muğla": "48",
    "mus": "49",
    "muş": "49",
    "nevsehir": "50",
    "nevşehir": "50",
    "nigde": "51",
    "niğde": "51",
    "ordu": "52",
    "rize": "53",
    "sakarya": "54",
    "samsun": "55",
    "siirt": "56",
    "sinop": "57",
    "sivas": "58",
    "tekirdag": "59",
    "tekirdağ": "59",
    "tokat": "60",
    "tunceli": "62",
    "sanliurfa": "63",
    "şanlıurfa": "63",
    "usak": "64",
    "uşak": "64",
    "van": "65",
    "yozgat": "66",
    "zonguldak": "67",
    "aksaray": "68",
    "bayburt": "69",
    "karaman": "70",
    "kirikkale": "71",
    "kırıkkale": "71",
    "batman": "72",
    "sirnak": "73",
    "şırnak": "73",
    "bartin": "74",
    "bartın": "74",
    "ardahan": "75",
    "igdir": "76",
    "ığdır": "76",
    "yalova": "77",
    "karabuk": "78",
    "karabük": "78",
    "kilis": "79",
    "osmaniye": "80",
    "duzce": "81",
    "düzce": "81",
}


def get_license_plate_for_city(city_key: str | None) -> str | None:
    """
    Get license plate number for a Turkish city key.
    
    Args:
        city_key: City key (e.g., "istanbul", "kirsehir")
        
    Returns:
        License plate number as string (e.g., "34", "40") or None if not found
    """
    if not city_key:
        return None
    
    # Normalize city key (lowercase, remove accents if needed)
    normalized = city_key.lower().strip()
    
    # Handle city keys that might have prefixes like "tr-istanbul"
    if "-" in normalized:
        parts = normalized.split("-")
        # Take the last part which should be the city name
        normalized = parts[-1]
    
    return TURKISH_CITY_PLATE_MAP.get(normalized)


def get_primary_license_plate(memleket: list[str] | None) -> str | None:
    """
    Get the primary license plate number from memleket array.
    Uses the first city in the array.
    
    Args:
        memleket: Array of Turkish city keys
        
    Returns:
        License plate number or None
    """
    if not memleket or len(memleket) == 0:
        return None
    
    # Use the first city as primary
    return get_license_plate_for_city(memleket[0])



