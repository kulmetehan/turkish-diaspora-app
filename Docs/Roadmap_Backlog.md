issue type,summary,description,status,priority,labels,story points,issue id,parent,acceptance criteria,definition of done,technical notes,risk level
Epic,Platform Foundation,"Alle backend-basisonderdelen voor identity, activity en infrastructuur.",Done,Medium,foundation,8,1,,"AC van de epic","DoD van de epic","Technische context",Medium
Story,Soft Identity & Client Tracking,"Implementeer X-Client-Id, automatische generatie, identity endpoint, koppeling aan activiteiten.",Done,Medium,"backend;identity",3,2,1,"AC 1","DoD 1","Tech notes 1",Medium
Story,Activity Stream Canonical Tables,"Maak canonical tabellen voor check-ins, reactions, notes, favorites en activity stream.",Done,Medium,"database;backend",5,3,1,"AC 2","DoD 2","Tech notes 2",Medium
Story,Activity Stream Ingest Worker,"Worker die alle events omzet naar activity_stream records.",Done,Medium,"backend;workers",5,4,1,"AC 3","DoD 3","Tech notes 3",Medium
Story,Privacy Settings Baseline,"Tabel bestaat. API en UI moeten nog worden ontwikkeld.",Done,Medium,"privacy;backend",3,5,1,"AC 4","DoD 4","Tech notes 4",Medium
Story,Rate Limiting Implementatie,"Integratie van rate limiting op alle interactie-endpoints: check-ins, reactions, notes, polls.",Done,High,"security;backend",5,6,1,"AC 5","DoD 5","Tech notes 5",High
Epic,Interaction Layer MVP,"Eerste interactieve laag van de app: check-ins, reactions, notes, feed en trending MVP.",Done,Medium,interaction,13,7,,"AC van de epic","DoD van de epic","Technische context",Medium
Story,Check-ins,"Volledige check-in flow met uniqueness + conflict 409 behavior.",Done,Medium,"interaction;backend",3,8,7,"AC 1","DoD 1","Tech notes 1",Medium
Story,Emoji Reactions,"Interactie met emoji's; uniqueness; aggregatie endpoints.",Done,Medium,"interaction;backend",3,9,7,"AC 2","DoD 2","Tech notes 2",Medium
Story,Location Notes,"Tekstnotities bij locaties; edit-logica; beperkingen op lengte.",Done,Medium,"interaction;backend",3,10,7,"AC 3","DoD 3","Tech notes 3",Medium
Story,Location Interaction Overview,"Endpoint voor check-ins, reactions en notes op locatiepagina's.",Done,Medium,backend,2,11,7,"AC 4","DoD 4","Tech notes 4",Medium
Story,Activity Stream Worker Integratie,"Koppelt alle user-activiteiten aan activity_stream tabel.",Done,Medium,"backend;workers",5,12,7,"AC 5","DoD 5","Tech notes 5",Medium
Story,Trending Indicator MVP,"Trending worker, ranking logica en API endpoints.",Done,Medium,"backend;trending",5,13,7,"AC 6","DoD 6","Tech notes 6",Medium
Story,Feed Tab - First UI Shell,"UI skeleton voor feedtab; placeholder vervangen door echte lijst.",Done,High,"frontend;interaction",8,14,7,"AC 7","DoD 7","Tech notes 7",High
Story,Diaspora Pulse Lite UI,"Eenvoudig dashboard voor trending metrics.",Done,Medium,"frontend;analytics",8,15,7,"AC 8","DoD 8","Tech notes 8",Medium
Epic,Engagement Layer,"Push notificaties, referrals, sharing en weekly digest.",Done,Medium,engagement,8,16,,"AC van de epic","DoD van de epic","Technische context",Medium
Story,Push Notifications,"Integreer push-notificaties via Firebase / Expo voor polls, trending en activity.",Done,High,"mobile;notifications",8,17,16,"AC 1","DoD 1","Tech notes 1",High
Story,Referral Program,"Referral systeem met unieke user codes en incentives.",Done,Medium,"backend;engagement",5,18,16,"AC 2","DoD 2","Tech notes 2",Medium
Story,Weekly Digest Email,"Genereer automatische email-samenvatting van trending, polls en activity.",Done,Medium,"backend;email",5,19,16,"AC 3","DoD 3","Tech notes 3",Medium
Story,Social Sharing UX,"Maak content shareable vanuit feed, reacties en trending.",Done,Medium,"frontend;sharing",3,20,16,"AC 4","DoD 4","Tech notes 4",Medium
Epic,Interaction Layer 2.0,"Diepere user layer: auth, profiles, XP, badges, favorites, polls, analytics.",Done,Medium,interaction2,21,21,,"AC van de epic","DoD van de epic","Technische context",Medium
Story,Supabase Auth Implementatie,"Volledige user login/signup flow met Google & Email.",Done,High,"auth;backend",8,22,21,"AC 1","DoD 1","Tech notes 1",High
Story,User Profiles API,"Profielbeheer: naam, avatar, bio, privacy settings.",Done,Medium,"backend;profiles",5,23,21,"AC 2","DoD 2","Tech notes 2",Medium
Story,Favorites API,"Favorieten toevoegen/verwijderen en ophalen per gebruiker.",Done,Medium,"backend;favorites",3,24,21,"AC 3","DoD 3","Tech notes 3",Medium
Story,XP Awarding Engine,"XP toe kennen bij check-ins, notes, reactions, poll responses.",Done,High,"gamification;backend",8,25,21,"AC 4","DoD 4","Tech notes 4",High
Story,Streaks & Badges Engine,"Streaks berekenen, badges toekennen op basis van XP of milestones.",Done,Medium,"gamification;backend",5,26,21,"AC 5","DoD 5","Tech notes 5",Medium
Story,Activity History UI,"UI waar gebruikers hun eigen activiteit kunnen zien.",Done,Medium,frontend,5,27,21,"AC 6","DoD 6","Tech notes 6",Medium
Story,Polls - Admin Creation UI,"Admin interface om dagelijkse polls te maken (vraag, opties, tijdsvenster).",Done,Medium,"frontend;admin",5,28,21,"AC 7","DoD 7","Tech notes 7",Medium
Story,Poll Response Logic,"Poll responses opslaan, valideren en XP toekennen.",Done,Medium,"backend;polls",3,29,21,"AC 8","DoD 8","Tech notes 8",Medium
Story,City & Category Stats,"API die statistieken geeft per stad en categorie op basis van activity stream & trending.",Done,Medium,"backend;analytics",8,30,21,"AC 9","DoD 9","Tech notes 9",Medium
Story,Diaspora Pulse Dashboard,"Volledig analytics dashboard met trending, activity, city stats.",Done,High,"frontend;analytics",13,31,21,"AC 10","DoD 10","Tech notes 10",High
Epic,Community Layer,"Groepen, moderators, reporting en guidelines.",Done,Low,community,13,32,,"AC van de epic","DoD van de epic","Technische context",Low
Story,User Groups,"Users kunnen groepen aanmaken/joinen.",Done,Low,"backend;frontend",8,33,32,"AC 1","DoD 1","Tech notes 1",Low
Story,Moderation Tools,"Admin tools voor spam reports, abusive users, content moderation.",Done,Medium,"backend;admin",8,34,32,"AC 2","DoD 2","Tech notes 2",Medium
Story,Reporting System,"Gebruikers kunnen notities, reacties en locaties rapporteren.",Done,Medium,"interaction;community",5,35,32,"AC 3","DoD 3","Tech notes 3",Medium
Story,Community Guidelines,"Inline UI + backend ondersteuning voor community rules.",Done,Low,"frontend;content",2,36,32,"AC 4","DoD 4","Tech notes 4",Low
Epic,Monetization Layer,"Business accounts, claiming, premium profiles, promoted content, Google Business integration.",Done,Medium,monetization,21,37,,"AC van de epic","DoD van de epic","Technische context",Medium
Story,Business Accounts API,"CRUD endpoints voor business accounts + koppeling aan locaties.",Done,Medium,"backend;business",5,38,37,"AC 1","DoD 1","Tech notes 1",Medium
Story,Location Claiming Flow,"Bedrijven kunnen hun locatie claimen met verificatie.",Done,High,"backend;business",8,39,37,"AC 2","DoD 2","Tech notes 2",High
Story,Verified Badge System,"Verified indicator voor geclaimde locaties + UI.",Done,Medium,"frontend;business",3,40,37,"AC 3","DoD 3","Tech notes 3",Medium
Story,Premium Features Layer,"Betaalmuur + extra locatie-informatie, statistieken en visuals.",Done,High,"backend;frontend;premium",13,41,37,"AC 4","DoD 4","Tech notes 4",High
Story,Promoted Locations,"Locaties kunnen omhoog in trending of feed in ruil voor betaling.",Done,Medium,"backend;monetization",8,42,37,"AC 5","DoD 5","Tech notes 5",Medium
Story,Promoted News,"Betaalde news posts bovenaan feed.",Done,Medium,"backend;monetization",5,43,37,"AC 6","DoD 6","Tech notes 6",Medium
Story,Business Analytics Dashboard,"Dashboard met views, likes, trending stats, engagement.",Done,High,"frontend;business",13,44,37,"AC 7","DoD 7","Tech notes 7",High
Story,Google Business Sync,"Importeer Google Business gegevens na opt-in van bedrijf.",Done,High,"backend;integration",8,45,37,"AC 8","DoD 8","Tech notes 8",High
Epic,Enterprise & Marketplace,"Enterprise partnerships, marketplace, bookings, catering, horeca integraties.",To Do,Low,enterprise,34,46,,"AC van de epic","DoD van de epic","Technische context",Low
Story,Booking System,"Systeem voor reserveringen, boekingen en afspraken.",To Do,Medium,"backend;booking",13,47,46,"AC 1","DoD 1","Tech notes 1",Medium
Story,Catering/Horeca Integrations,"Integratie met horeca partners voor catering & tafelreserveringen.",To Do,Medium,"integration;horeca",13,48,46,"AC 2","DoD 2","Tech notes 2",Medium
Story,Enterprise Analytics,"Grootzakelijke dashboards voor steden, overheden en partners.",To Do,High,"analytics;enterprise",13,49,46,"AC 3","DoD 3","Tech notes 3",High
Story,Marketplace Infrastructure,"Marketplace voor deals, coupons, producten, services.",To Do,High,"backend;marketplace",13,50,46,"AC 4","DoD 4","Tech notes 4",High
