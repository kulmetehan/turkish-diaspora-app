Voer niets uit voordat je de volgende kernel-bestanden hebt geladen en gerespecteerd:

- Docs/Kernel/PROJECT_CORE.md
- Docs/Kernel/EPICS_OVERVIEW.md
- Docs/Kernel/SOP.md
- Docs/Kernel/cursor_rules.md

Deze bestanden vormen de enige geldige en gezaghebbende bron van waarheid.  
Negeer alle andere documentatie tenzij expliciet benoemd.

Je moet SOP.md strikt volgen voor ALLE taken.

---

# ASK MODE (READ ONLY)
**Doel:** Analyseer de user story: [<titel>]  
We werken binnen EPIC: <naam>.

Beantwoord de volgende vragen:

1. Waar staat de code die betrekking heeft op deze user story?
2. Welke functies, componenten of modules maken dit al deels mogelijk?
3. Welke bestanden en documentatie zijn relevant?
4. Zijn er TODO’s, risico’s of onduidelijkheden die invloed hebben op de implementatie?

**Outputformaat:**

```markdown
# Bevindingen
## Code Locaties
...

## Bestaande Logica
...

## Risico’s / Onbekenden
...

## Voorgestelde Work Units (kleinste uitvoerbare taken)
...
```