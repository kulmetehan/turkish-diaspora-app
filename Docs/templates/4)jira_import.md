Handleiding & Standaard Template voor Jira CSV Imports (TDA Project)

🎯 Doel

Dit document definieert het enige correcte CSV-formaat voor Jira Cloud import in dit project.
We gebruiken het Parent / Issue ID model volgens Atlassian (vanaf 2024), aangezien:
	•	Epic Link is deprecated
	•	Epic Name wordt niet meer gebruikt door Jira Cloud
	•	Parent is nu het enige middel om hiërarchieën te creëren
	•	Alle work items moeten in juiste volgorde staan tijdens import

Dit document garandeert dat toekomstige Jira CSV-imports altijd werken zonder errors.

⸻

🧱 Structuur van Work Items

In Jira Cloud (nieuw model):

Niveau	Jira Issue Type
1	Epic
2	Story / Task / Bug
3	Sub-task (optioneel, niet gebruikt in dit project)


⸻

📂 Vereiste CSV-kolommen

Jira vereist minimaal deze kolommen:
	•	issue type
	•	summary
	•	issue id
	•	parent

Het TDA-project gebruikt daarnaast:
	•	description
	•	status
	•	priority
	•	labels
	•	story points
	•	acceptance criteria
	•	definition of done
	•	technical notes
	•	risk level

Jira zal automatisch custom fields aanmaken als ze nog niet bestaan.

⸻

📌 Belangrijke Regels

1. Gebruik NOOIT deze kolommen:
	•	Epic Link ❌
	•	Epic Name ❌
	•	Components ❌
	•	Parent Link ❌

Deze werken niet meer met Jira Cloud.

⸻

2. Gebruik ALLEEN de Jira Cloud structuur:

Epic krijgt:

issue type = Epic
issue id = 1
parent = (leeg)

Stories krijgen:

issue type = Story
parent = 1
issue id = uniek nummer (2,3,4...)


⸻

3. Volgorde is kritisch

De volgorde in de CSV moet zijn:
	1.	Epic(s)
	2.	Stories
	3.	Sub-tasks (optioneel)

⸻

📥 Standaard CSV Template

Onderstaand sjabloon kan zonder aanpassingen worden gebruikt.
Je hoeft alleen de items toe te voegen of te wijzigen.

issue type,summary,description,status,priority,labels,story points,issue id,parent,acceptance criteria,definition of done,technical notes,risk level
Epic,EPIC TITLE,"Epic beschrijving hier",To Do,High,"label1 label2",,1,,"AC van de epic","DoD van de epic","Technische context",High
Story,Story titel 1,"Beschrijving van story 1",To Do,Medium,"label1",3,2,1,"AC 1","DoD 1","Tech notes 1",Medium
Story,Story titel 2,"Beschrijving van story 2",To Do,Medium,"label1 label2",5,3,1,"AC 2","DoD 2","Tech notes 2",Low
Story,Story titel 3,"Beschrijving van story 3",To Do,High,"ai backend",8,4,1,"AC 3","DoD 3","Tech notes 3",High

✔️ Tips voor correct gebruik:
	•	Elke issue id moet uniek zijn
	•	parent moet verwijzen naar een eerder gedefinieerd issue id
	•	Gebruik GEEN speciale tekens in kolomnamen

⸻

🧩 Mapping in Jira Import Wizard

Tijdens import:

CSV Field	Jira Field
issue type	Issue Type
summary	Summary
description	Description
issue id	Issue ID
parent	Parent
status	Status
priority	Priority
labels	Labels
story points	Story Points
acceptance criteria	(nieuw custom field)
definition of done	(nieuw custom field)
technical notes	(nieuw custom field)
risk level	(nieuw custom field)


⸻

🛠️ Import Stappen
	1.	Ga naar
Jira → Settings → System → External System Import → CSV
	2.	Kies Switch to old importer
	3.	Upload CSV
	4.	Map de velden zoals hierboven
	5.	Zorg dat Parent gemapped kan worden
→ Sub-tasks moeten ingeschakeld zijn in:
Settings → Issues → Sub-tasks
	6.	Klik Begin import

⸻

🚨 Troubleshooting

Error: Cannot set value for locked custom field ‘Epic Name’

→ Je hebt nog ergens in je CSV een kolom Epic Name staan.
Oplossing: Verwijder deze volledig.

⸻

Error: Cannot add value [X] to Epic Link

→ Je gebruikt een Epic Link kolom.
Oplossing: verwijder Epic Link kolom.

⸻

Parent kolom bestaat niet in import mapping

→ Sub-tasks staan uit.
Oplossing:
Enable hier:
https://<jouw_jira>.atlassian.net/secure/admin/subtasks/ManageSubTasks.jspa

⸻

Story wordt niet gekoppeld aan Epic

→ Parent verwijst niet naar de juiste issue id.
Oplossing:
Zorg dat:

Epic:
issue id = 1

Story:
parent = 1


⸻

🧾 Voorbeeld van juiste structuur (visueel)

1   Epic      "TDA-NEWS – Diaspora..."
2   Story      RSS Config
3   Story      RSS Worker
4   Story      AI Pipeline
5   Story      Frontend Views
...


⸻

🎯 Conclusie

Door altijd dit template te gebruiken en de regels in dit document te volgen:
	•	zijn imports 100% foutloos
	•	werkt parent-child relatie altijd
	•	wordt het consistent binnen alle toekomstige TDA epics
	•	blijft Jira schoon, logisch en schaalbaar

⸻

Hier is de exacte CSV-header die we altijd gaan gebruiken voor alle Jira-imports binnen het project:

issue type,summary,description,status,priority,labels,story points,issue id,parent,acceptance criteria,definition of done,technical notes,risk level

✔️ Deze header is volledig Jira Cloud-compatible
✔️ Gebaseerd op het nieuwe Parent / Issue ID model
✔️ Geen deprecated velden (Epic Link, Epic Name, Components etc.)
✔️ Custom fields worden automatisch aangemaakt
✔️ Stories koppelen automatisch aan de Epic via parent

**Note**: De actuele backlog die klaar is voor import staat in [`Docs/Roadmap_Backlog.md`](../Roadmap_Backlog.md). Deze gebruikt het bovenstaande formaat zonder "Epic Name" kolom.