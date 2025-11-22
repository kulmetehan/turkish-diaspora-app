# SOP.md
**Standard Operating Procedure — Turkish Diaspora App**  
_Versie 1.0_

---

# ⭐ 0. Kernregel
Elke taak doorloopt ALTIJD deze cyclus:

**IDEA → BREAKDOWN → ANALYSIS → PLAN → APPLY → REVIEW → DOCUMENT**

Geen uitzonderingen.

---

# 1. IDEA PHASE (door gebruiker)
Jij levert een ruwe gedachte:  
> “Ik denk dat we X moeten bouwen”

Geen structuur vereist.

---

# 2. BREAKDOWN PHASE (ChatGPT)
ChatGPT maakt:

1. Epic mapping
2. Kleinste mogelijke User Stories
3. Prioriteit & afhankelijkheden
4. Risico’s
5. Volgorde van realisatie

Output:

```md
# Breakdown
Epic: …
User Stories:
- US-…
Risico’s:
…
```

---

# 3. ANALYSIS (Cursor Ask Mode)
Cursor wordt altijd eerst gebruikt in **READ ONLY**.

Template:

```md
You are in ASK MODE.
Goal: Analyse user story <US>.
Respect:
- PROJECT_CORE.md
- EPICS_OVERVIEW.md
- SOP.md

Deliver:
# Findings
## Code Locations
## Existing Logic
## Risks
## Suggested Work Units
```

---

# 4. PLAN MODE (ChatGPT)
ChatGPT maakt:

- Mini-stappenplan  
- Acceptatiecriteria  
- Scope-afbakening  
- Impact op systeem  

---

# 5. APPLY MODE (Cursor)
Cursor voert **één Work Unit tegelijk** uit.

Regels:
1. Stop bij onzekerheid  
2. Pas code niet buiten scope aan  
3. Schrijf altijd impacted files lijst  
4. Elke Work Unit = commit

---

# 6. REVIEW (ChatGPT)
ChatGPT beoordeelt:

- Is het logisch?  
- Side-effects?  
- Regressies?  
- Zijn alle criteria gehaald?

---

# 7. DOCUMENTATION UPDATE (Cursor / ChatGPT)
Elke user story krijgt:

```md
/Docs/EPIC/US-XX.md
```

Inhoud:
- What changed  
- Why  
- Files updated  
- Future considerations  

Documentatie is verplicht onderdeel van DONE.