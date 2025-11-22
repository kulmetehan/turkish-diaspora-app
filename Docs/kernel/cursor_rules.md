# cursor_rules.md
**Cursor Safety & Execution Rules**  
_Versie 1.0_

---

# 1. Respect Project Kernel
Je moet ALTIJD de volgende bestanden inlezen vóór je begint:

- PROJECT_CORE.md  
- EPICS_OVERVIEW.md  
- SOP.md  

---

# 2. Safety Rules
1. No assumptions — ONLY code facts.
2. Never modify unrelated files.
3. Never modify DB schema zonder expliciete human approval.
4. Maximaal **1 Work Unit per run**.
5. If unclear → STOP and request clarification.
6. Documenteer impacted files na elke actie.
7. Volg SOP strikt: ANALYSIS → PLAN → APPLY → REVIEW.
8. Agent Mode moet stoppen bij ambiguïteit.

---

# 3. Stijlregels
- Prefer clarity over brevity  
- Geen grote PR’s  
- Atomic commits  
- Consistent formatting  

---

# 4. Error Conditions
Stop wanneer:
- Bestanden onvindbaar zijn  
- Functies inconsistent zijn  
- Onverwachte side-effects optreden  
- De user story grenzen overschrijdt  

---

# 5. Completion
Na elke Work Unit:

```md
# Completed
Files changed:
- ...
Next recommended step:
- ...
```