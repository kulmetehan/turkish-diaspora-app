# City Grid Definitions (Rotterdam)

Deze pagina beschrijft de structuur en het gebruik van `/Infra/config/cities.yml`. DiscoveryBot gebruikt deze configuratie om **multi-grid discovery-runs** te draaien per wijk/stadsdeel van Rotterdam. Dit volgt de EPIC “Data-Ops & AI Expansion” en de deliverable “City-grid definities”.  
Zie ook: DiscoveryBot (grid-based search) en Google Places integratie.  
Bronnen: The New Testament II (Roadmap Fase 2), D2-S2 (City-Grid Definitions), TDA-8 (DiscoveryBot), TDA-7 (Google Service), TDA-C2-S6 (Type Mapping). :contentReference[oaicite:6]{index=6} :contentReference[oaicite:7]{index=7} :contentReference[oaicite:8]{index=8} :contentReference[oaicite:9]{index=9} 

---

## Bestandsstructuur

```yaml
version: 1
metadata: {...}
defaults: {...}           # grid & nearby defaults
cities:
  rotterdam:
    city_name: "Rotterdam"
    country: "NL"
    apply: *rotterdam_defaults
    districts:
      <district_key>:
        lat_min: <float>
        lat_max: <float>
        lng_min: <float>
        lng_max: <float>
        apply: *rotterdam_defaults
