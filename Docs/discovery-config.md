# Discovery Config – Categories & Google `place_types`

Deze guide beschrijft hoe `Infra/config/categories.yml` de **diaspora-categorieën** koppelt aan **Google `place_types`**. DiscoveryBot gebruikt deze mapping om quota-efficiënt te zoeken en de AI-laag behoudt consistente categorie-labels.

## Doel & Context

- **Discovery (TDA-7):** gebruikt `included_types` + field masks voor lean requests en betere deduplicatie.  
- **AI (TDA-10):** valideert outputs en logt alles in `ai_logs` met consistente `category`.  
- **Admin/Gold (TDA-18):** houdt audit & gold records in sync met dezelfde categorie-sleutels.  

Zie ook de roadmap die `categories.yml` als bron noemt.  
*(Bron: TDA-7, TDA-10, TDA-18, The New Testament II)*

## YAML-structuur

```yaml
version: 1
defaults:
  language: "nl"
  region: "NL"
  discovery:
    nearby_radius_m: 1000
    max_per_cell_per_category: 20

categories:
  <category_key>:
    label: "<weergavenaam>"
    description: "<korte omschrijving>"
    google_types:
      - "<google_place_type_1>"
      - "<google_place_type_2>"
    aliases:
      - "<synoniem_of_TR-term>"
    discovery:
      enabled: true
      priority: <int>
