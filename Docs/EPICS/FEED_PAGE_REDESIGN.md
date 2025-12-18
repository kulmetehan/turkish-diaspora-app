# Epic: FeedPage Redesign naar Mobile-First Landing Page

**Status**: 🟡 In Progress  
**Gemaakt**: 2025-01-XX  
**Laatste update**: 2025-01-28  
**Geschatte totale tijd**: 30-42 uur  
**Voltooid**: Fase 1 (Backend API Uitbreidingen) ✅, Fase 2 (Nieuwe UI Componenten) ✅, Fase 3 (FeedCard Herontwerp) ✅, Fase 4 (FeedPage Herontwerp) ✅

---

## 📋 Overzicht

Dit epic beschrijft de volledige herontwerp van de FeedPage naar een mobile-first landing page zoals gespecificeerd in de ChatGPT samenvatting. De pagina moet het eerste scherm zijn na app-open en direct persoonlijke relevantie en lokale community activiteit tonen.

**Doel**: Transformeren van de huidige tab-gebaseerde FeedPage naar een moderne, mobile-first feed experience met:
- Persoonlijke greeting met user name
- Search functionaliteit
- Horizontaal scrollbare filter pills
- Moderne feed cards met user avatars, likes, bookmarks en media
- App header met logo en notifications

---

## 🔍 Gap Analysis

### 1. Pagina Structuur & Layout

| Component | Huidige Situatie | Gewenste Situatie | Status |
|-----------|------------------|-------------------|--------|
| **FeedPage Container** | Tab-gebaseerd (Activity/Trending/Polls/Bulletin), gebruikt PageShell | Simpele verticale layout, mobile-first, scrollbaar, geen PageShell | ✅ Voltooid (Fase 4) |
| **AppHeader** | Geen | Logo links ("Komşu"), notification bell rechts, static | ✅ Voltooid (Fase 2) |
| **GreetingBlock** | Geen | "Good Morning, [Naam]" + subtitle | ✅ Voltooid (Fase 2) |
| **SearchInput** | Geen | Zoekbalk met search icon | ✅ Voltooid (Fase 2) |
| **FeedFilterTabs** | Genest in Tabs component, niet scrollbaar | Horizontaal scrollbare pills | ✅ Voltooid (Fase 2) |
| **FeedList** | ActivityFeed met loading/error states | FeedList container voor FeedCards | ✅ Voltooid (Fase 3) |
| **FeedCard** | ActivityCard met icon, geen user avatar | Volledige card met user avatar, name, content, media, likes, bookmarks | ✅ Voltooid (Fase 3) |
| **EventBadge** | Geen | Badge voor event-type items | ✅ Voltooid (Fase 2) |
| **BottomNavigation** | FooterTabs bestaat (5 tabs) | Zelfde, maar verificatie nodig | ✅ Bestaat |

### 2. Data & API

| Feature | Huidige Situatie | Gewenste Situatie | Status |
|---------|------------------|-------------------|--------|
| **User info in feed** | "Iemand" hardcoded, geen user data | User avatar, name per item | ✅ Voltooid (Fase 1) |
| **ActivityItem type** | Geen user_id, avatar, name | user object met avatar/name | ✅ Voltooid (Fase 1) |
| **Like functionaliteit** | Geen | likeCount, isLiked | ✅ Voltooid (Fase 1) |
| **Bookmark functionaliteit** | Alleen voor News | Bookmark op feed items | ✅ Voltooid (Fase 1) |
| **Media support** | Geen | mediaUrl optioneel | ✅ Voltooid (Fase 1) |
| **Event type** | Geen specifiek event type | type: "event" met EventBadge | ✅ Voltooid (Fase 1) |
| **User greeting** | Geen user name beschikbaar | User profile naam ophalen | ✅ Voltooid (Fase 1) |

### 3. UX/UI Details

| Aspect | Huidige Situatie | Gewenste Situatie | Status |
|--------|------------------|-------------------|--------|
| **Mobile-first** | Niet specifiek mobile-first | Mobile-first, safe-area aware | ✅ Voltooid (Fase 4) |
| **Card design** | Eenvoudige border/shadow | Witte card, rounded, zachte shadow, media full-width | ✅ Voltooid (Fase 3) |
| **Filter pills** | TabsList component | Horizontaal scrollbare pills, active/inactive states | ✅ Voltooid (Fase 2) |
| **Search** | Geen | Zoekinput met icon, filter functionaliteit | ✅ Voltooid (Fase 4) |
| **Personalisatie** | Geen | Greeting met user name | ✅ Voltooid (Fase 4) |

### 4. Functionaliteit

| Feature | Huidige Situatie | Gewenste Situatie | Status |
|---------|------------------|-------------------|--------|
| **Search/filter** | Alleen filter tabs | Search input + filter tabs | ✅ Voltooid (Fase 4) |
| **Like toggle** | Geen | Like/unlike met count | ✅ Voltooid (Fase 4) |
| **Bookmark toggle** | Geen | Bookmark/unbookmark | ✅ Voltooid (Fase 4) |
| **Media display** | Geen | Optionele image in card | ✅ Voltooid (Fase 3) |
| **Event badge** | Geen | Badge overlay op event items | ✅ Voltooid (Fase 3) |

---

## 📋 Implementatie Plan (Kanban Board)

### ✅ Done (Afgerond)

#### Fase 1: Backend API Uitbreidingen ✅ (Voltooid: 2025-01-27)

**Status**: Alle backend API uitbreidingen zijn voltooid en database migraties zijn uitgevoerd.

- [x] **TASK-1.1**: Activity Stream API uitbreiden met user info ✅
  - **Beschrijving**: User info toevoegen aan activity stream response (user_id, user_name, user_avatar_url)
  - **Bestanden**: `Backend/api/routers/activity.py`, `Frontend/src/lib/api.ts`
  - **API Contract**: 
    ```python
    ActivityItem {
      user: {
        id: int,
        name: string,
        avatar_url: string | null
      },
      ...
    }
    ```
  - **Voltooid**: 2025-01-27
  - **Uitgevoerd**: 
    - ActivityUser model toegevoegd met id, name, avatar_url
    - JOIN met user_profiles tabel in alle 3 activity endpoints
    - Frontend TypeScript types bijgewerkt
  - **Database migraties**: Geen nieuwe migraties nodig (gebruikt bestaande user_profiles tabel)

- [x] **TASK-1.2**: Event type ondersteuning toevoegen ✅
  - **Beschrijving**: Event type toevoegen aan activity_type enum en handling
  - **Bestanden**: `Backend/api/routers/activity.py`, `Frontend/src/lib/api.ts`
  - **Voltooid**: 2025-01-27
  - **Uitgevoerd**:
    - Database migratie 053: Event type toegevoegd aan constraint
    - valid_types lijst bijgewerkt
    - TypeScript type bijgewerkt

- [x] **TASK-1.3**: Media URL ondersteuning toevoegen ✅
  - **Beschrijving**: Optionele media_url toevoegen aan activity items
  - **Bestanden**: `Backend/api/routers/activity.py`, `Frontend/src/lib/api.ts`
  - **Voltooid**: 2025-01-27
  - **Uitgevoerd**:
    - Database migratie 054: media_url kolom toegevoegd aan activity_stream
    - ActivityItem model bijgewerkt met media_url veld
    - Alle 3 SQL queries bijgewerkt
    - Frontend TypeScript types bijgewerkt

- [x] **TASK-1.4**: Like functionaliteit implementeren ✅
  - **Beschrijving**: Like counts en isLiked status per item toevoegen
  - **Bestanden**: `Backend/api/routers/activity.py`, `Frontend/src/lib/api.ts`
  - **Voltooid**: 2025-01-27
  - **Uitgevoerd**:
    - Database migratie 055: activity_likes tabel aangemaakt met unique indexes
    - ActivityItem model bijgewerkt met like_count en is_liked
    - Alle 3 SQL queries bijgewerkt met JOINs voor like counts
    - Nieuwe endpoint: POST `/api/v1/activity/{id}/like`
    - Frontend API functie: `toggleActivityLike()`

- [x] **TASK-1.5**: Bookmark functionaliteit implementeren ✅
  - **Beschrijving**: Bookmark status per item toevoegen (vergelijkbaar met News bookmarks)
  - **Bestanden**: `Backend/api/routers/activity.py`, `Frontend/src/lib/api.ts`
  - **Voltooid**: 2025-01-27
  - **Uitgevoerd**:
    - Database migratie 056: activity_bookmarks tabel aangemaakt met unique indexes
    - ActivityItem model bijgewerkt met is_bookmarked
    - Alle 3 SQL queries bijgewerkt met JOINs voor bookmarks
    - Nieuwe endpoint: POST `/api/v1/activity/{id}/bookmark`
    - Frontend API functie: `toggleActivityBookmark()`

- [x] **TASK-1.6**: User Profile API endpoint ✅
  - **Beschrijving**: Endpoint voor huidige user (naam, avatar) voor GreetingBlock
  - **API Endpoint**: GET `/api/v1/users/me`
  - **Bestanden**: `Backend/api/routers/profiles.py`
  - **Voltooid**: 2025-01-27
  - **Uitgevoerd**:
    - Nieuwe endpoint toegevoegd aan profiles router
    - Retourneert None voor anonymous users (auth TODO voor later)

**Fase 1 Samenvatting**:
- ✅ 4 database migraties uitgevoerd (053-056)
- ✅ Activity Stream API volledig uitgebreid met user info, likes, bookmarks, media
- ✅ 2 nieuwe endpoints toegevoegd (like en bookmark toggle)
- ✅ Frontend TypeScript types volledig bijgewerkt
- ✅ Alle wijzigingen zijn backward compatible

---

#### Fase 2: Nieuwe UI Componenten ✅ (Voltooid: 2025-01-27)

**Status**: Alle UI componenten voor Fase 2 zijn voltooid en klaar voor gebruik in Fase 4.

- [x] **TASK-2.1**: AppHeader component ✅
  - **Beschrijving**: Header met logo links en notification bell rechts
  - **Bestand**: `Frontend/src/components/feed/AppHeader.tsx`
  - **Props**: `{ onNotificationClick?: () => void }`
  - **Features**: 
    - Logo/wordmark "Komşu" links
    - Bell icon rechts (round touch target)
    - Static position, geen background (gradient van page)
  - **Voltooid**: 2025-01-27
  - **Uitgevoerd**: 
    - Component geïmplementeerd met Icon component voor bell
    - Safe-area support toegevoegd voor iOS
    - Touch target minimaal 44x44px
    - Static positioning zonder fixed header

- [x] **TASK-2.2**: GreetingBlock component ✅
  - **Beschrijving**: Personalized greeting met user name en time-based message
  - **Bestand**: `Frontend/src/components/feed/GreetingBlock.tsx`
  - **Props**: `{ userName?: string | null }`
  - **Features**: 
    - Time-based greeting (Good Morning/Afternoon/Evening)
    - Dynamic name accent (brand color)
    - Subtitle: "What's happening in your community"
  - **Voltooid**: 2025-01-27
  - **Uitgevoerd**:
    - Helper functie `getTimeBasedGreeting()` geïmplementeerd
    - User name met primary color accent
    - Fallback voor anonymous users (geen name weergegeven)

- [x] **TASK-2.2**: User Profile API functie ✅
  - **Beschrijving**: API functie voor user profile ophalen
  - **Bestand**: `Frontend/src/lib/api.ts`
  - **Functie**: `getCurrentUser()` → `Promise<CurrentUser | null>`
  - **Voltooid**: 2025-01-27
  - **Uitgevoerd**:
    - Nieuwe `getCurrentUser()` functie toegevoegd
    - `CurrentUser` interface gedefinieerd met name en avatar_url
    - Error handling voor anonymous users (retourneert null)

- [x] **TASK-2.3**: SearchInput component ✅
  - **Beschrijving**: Rounded search input met icon
  - **Bestand**: `Frontend/src/components/feed/SearchInput.tsx`
  - **Props**: `{ value: string, onChange: (value: string) => void, placeholder?: string }`
  - **Features**: 
    - Fully rounded input
    - Search icon links in input
    - Placeholder: "Search by name or category"
    - Primary action feel
  - **Voltooid**: 2025-01-27
  - **Uitgevoerd**:
    - Gebaseerd op bestaand Input component
    - Search icon gepositioneerd met absolute positioning
    - Fully rounded borders (`rounded-full`)

- [x] **TASK-2.4**: FeedFilterTabs component (herwerken) ✅
  - **Beschrijving**: Horizontaal scrollbare filter pills
  - **Bestand**: `Frontend/src/components/feed/FeedFilterTabs.tsx`
  - **Props**: `{ activeFilter: ActivityFilter, onFilterChange: (filter: ActivityFilter) => void }`
  - **Features**: 
    - Horizontal scroll (overflow-x)
    - Pills/rounded buttons design
    - Active: dark bg (`bg-primary`), light text
    - Inactive: light bg (`bg-muted`), dark text
    - Compact height, clear spacing
  - **Filters**: `["All", "Check-ins", "Events", "Reactions", "Notes", "Polls", "Favorites", "Bulletin"]`
  - **Voltooid**: 2025-01-27
  - **Uitgevoerd**:
    - Horizontaal scrollbare pills implementatie
    - Active/inactive states met duidelijk visueel onderscheid
    - TypeScript type `ActivityFilter` geëxporteerd
    - Scrollbar verborgen via CSS (webkit + Firefox support)
    - Filter mapping: labels naar activity_type values

- [x] **TASK-2.5**: EventBadge component ✅
  - **Beschrijving**: Badge voor event-type items
  - **Bestand**: `Frontend/src/components/feed/EventBadge.tsx`
  - **Props**: `{ label?: string }` (default: "Event")
  - **Features**: 
    - Rode pill badge
    - Absolute position over image (top-left)
    - Alleen zichtbaar bij type = event
  - **Voltooid**: 2025-01-27
  - **Uitgevoerd**:
    - Badge component met brand-red achtergrond
    - Absolute positioning voor overlay op images
    - Compact design met shadow

**Fase 2 Samenvatting**:
- ✅ 5 nieuwe UI componenten geïmplementeerd
- ✅ 1 API functie toegevoegd (`getCurrentUser()`)
- ✅ Alle componenten mobile-first en responsive
- ✅ TypeScript types volledig gedefinieerd
- ✅ Componenten gebruiken bestaande design system patterns
- ✅ CSS utility toegevoegd voor scrollbar hiding

---

### ✅ Done (Afgerond)

#### Fase 3: FeedCard Herontwerp ✅ (Voltooid: 2025-01-28)

**Status**: Alle componenten voor Fase 3 zijn voltooid en geïntegreerd in Fase 4.

- [x] **TASK-3.1**: FeedCard component (volledig herontwerp) ✅
  - **Beschrijving**: Moderne feed card met alle features
  - **Bestand**: `Frontend/src/components/feed/FeedCard.tsx`
  - **Props**:
    ```typescript
    {
      user: { avatar: string, name: string },
      locationName: string,
      timestamp: string,
      contentText: string,
      mediaUrl?: string,
      likeCount: number,
      isLiked: boolean,
      isBookmarked: boolean,
      type: "check-in" | "event" | "reaction" | "note" | "poll_response" | "favorite" | "bulletin_post",
      onLike?: () => void,
      onBookmark?: () => void,
      onClick?: () => void
    }
    ```
  - **Structuur**:
    - Header: Avatar + Name + Meta (location · time)
    - Content text
    - Media image (optioneel, full-width)
    - Action row: Like icon + count, Bookmark icon
    - EventBadge (conditional)
  - **Design**: White card, rounded corners, soft shadow
  - **Geschatte tijd**: 4-5 uur
  - **Voltooid**: 2025-01-28
  - **Uitgevoerd**:
    - Component geïmplementeerd met user avatar (met fallback naar initialen)
    - Like en bookmark functionaliteit geïntegreerd
    - Media image support met error handling
    - EventBadge overlay voor event items
    - Responsive design met proper spacing
    - Timestamp formatting (hergebruikt van ActivityCard)
    - Click navigation voor location detail en bulletin posts

- [x] **TASK-3.2**: FeedList component ✅
  - **Beschrijving**: Container voor FeedCards met spacing en loading states
  - **Bestand**: `Frontend/src/components/feed/FeedList.tsx`
  - **Props**: `{ items: FeedItem[], onLoadMore?: () => void, isLoading?: boolean }`
  - **Features**: 
    - Vertical stack
    - Spacing tussen cards
    - Loading/empty states
    - Infinite scroll of "Load More" button
  - **Geschatte tijd**: 2 uur
  - **Voltooid**: 2025-01-28
  - **Uitgevoerd**:
    - Container component met spacing tussen cards
    - Loading states met skeleton loaders
    - Empty states met custom messages
    - Pagination met "Meer laden" button
    - Error handling

**Fase 3 Samenvatting**:
- ✅ FeedCard component volledig geïmplementeerd met alle features
- ✅ FeedList component geïmplementeerd met loading/empty states
- ✅ Beide componenten mobile-first en responsive
- ✅ TypeScript types volledig gedefinieerd
- ✅ Componenten klaar voor integratie in FeedPage

---

#### Fase 4: FeedPage Herontwerp ✅ (Voltooid: 2025-01-28)

**Status**: FeedPage volledig herontworpen naar mobile-first landing page met alle nieuwe componenten geïntegreerd.

- [x] **TASK-4.1**: FeedPage component restructureren ✅
  - **Beschrijving**: Volledige herstructurering naar nieuwe layout
  - **Bestand**: `Frontend/src/pages/FeedPage.tsx`
  - **Nieuwe Structuur**:
    ```tsx
    <FeedPage>
      <AppHeader />
      <GreetingBlock userName={userName} />
      <SearchInput value={search} onChange={...} />
      <FeedFilterTabs activeFilter={filter} onFilterChange={...} />
      <FeedList items={feedItems} />
      <FooterTabs /> {/* Bestaand component */}
    </FeedPage>
    ```
  - **State Management**:
    - Search query state
    - Active filter state
    - Feed items state
    - Loading/error states
    - Pagination state
  - **Geschatte tijd**: 4-5 uur
  - **Voltooid**: 2025-01-28
  - **Uitgevoerd**:
    - Volledige herstructurering: verwijderd Tabs, PageShell, nested structure
    - Nieuwe layout met AppHeader, GreetingBlock, SearchInput, FeedFilterTabs, FeedList, FooterTabs
    - State management voor search, filter, pagination, loading, errors
    - Mobile-first verticale scrollbare layout
    - FooterTabs geïntegreerd (bestaand component)

- [x] **TASK-4.2**: Data transformatie & integratie ✅
  - **Beschrijving**: ActivityItem transformeren naar FeedCard props
  - **Bestanden**: `Frontend/src/pages/FeedPage.tsx`, helper functions
  - **Features**: 
    - Map ActivityItem[] naar FeedCard props
    - Handle user data
    - Handle media URLs
    - Format timestamps
  - **Geschatte tijd**: 2-3 uur
  - **Voltooid**: 2025-01-28
  - **Uitgevoerd**:
    - `transformActivityItem()` helper functie geïmplementeerd
    - Integratie met `getActivityFeed()` API
    - Pagination met `handleLoadMore()` functie
    - Hergebruik van `getActivityMessage()` logica uit ActivityCard
    - Timestamp formatting
    - User data handling met fallbacks

- [x] **TASK-4.3**: Search functionaliteit ✅
  - **Beschrijving**: Search input verbinden met feed filtering
  - **Bestanden**: `Frontend/src/pages/FeedPage.tsx`
  - **Features**: 
    - Client-side filtering of API search
    - Debounced search input
    - Filter op name/category
  - **Geschatte tijd**: 2-3 uur
  - **Voltooid**: 2025-01-28
  - **Uitgevoerd**:
    - Client-side filtering met 300ms debounce
    - Search in location name, user name, en content text
    - Combineert met filter tabs (API filter + client-side search)
    - Empty state messages voor search results
    - Case-insensitive matching

- [x] **TASK-4.4**: User data ophalen voor greeting ✅
  - **Beschrijving**: User profile ophalen en tonen in GreetingBlock
  - **Bestanden**: `Frontend/src/pages/FeedPage.tsx`, hooks
  - **Features**: 
    - Fetch user profile op mount
    - Handle loading/error states
    - Fallback voor anonymous users
  - **Geschatte tijd**: 1-2 uur
  - **Voltooid**: 2025-01-28
  - **Uitgevoerd**:
    - `getCurrentUser()` call op component mount
    - Silent error handling (geen toast voor anonymous users)
    - User name geïntegreerd in GreetingBlock
    - Fallback voor anonymous users (geen name weergegeven)

**Fase 4 Samenvatting**:
- ✅ FeedPage volledig herontworpen naar mobile-first landing page
- ✅ Alle Phase 2 componenten geïntegreerd (AppHeader, GreetingBlock, SearchInput, FeedFilterTabs)
- ✅ FeedCard en FeedList componenten geïntegreerd
- ✅ Data transformatie en API integratie compleet
- ✅ Search functionaliteit met debounce geïmplementeerd
- ✅ User data fetching voor personalized greeting
- ✅ Like en bookmark functionaliteit geïntegreerd met optimistic updates
- ✅ Pagination en loading states volledig geïmplementeerd
- ✅ Error handling en empty states
- ✅ Mobile-first responsive design

**Nieuwe Bestanden**:
- `Frontend/src/components/feed/FeedCard.tsx` - Moderne feed card component
- `Frontend/src/components/feed/FeedList.tsx` - Container voor FeedCards
- `Frontend/src/pages/FeedPage.tsx` - Volledig herontworpen FeedPage

**Belangrijke Wijzigingen**:
- FeedPage gebruikt nu AppViewportShell direct (geen PageShell meer)
- Geen tab structuur meer (Activity/Trending/Polls/Bulletin verwijderd)
- Nieuwe verticale scrollbare layout
- Search functionaliteit met client-side filtering
- Like en bookmark toggles met optimistic updates

---

### ✅ Done (Afgerond)

#### Fase 5: Functionaliteit & Polish ✅ (Voltooid: 2025-01-28)

**Status**: Alle feed card polish verbeteringen zijn voltooid.

- [x] **TASK-5.1**: Relative time formatting ✅
  - **Beschrijving**: Update time formatting voor < 24h (minuten/uren) en >= 24h (exacte datum)
  - **Bestanden**: `Frontend/src/components/feed/FeedCard.tsx`
  - **Voltooid**: 2025-01-28
  - **Uitgevoerd**: formatActivityTime() functie bijgewerkt met 24h threshold

- [x] **TASK-5.2**: Clickable content & deep linking ✅
  - **Beschrijving**: Poll preview, note preview, location links, reaction links
  - **Bestanden**: `Frontend/src/components/feed/FeedCard.tsx`, `Frontend/src/pages/FeedPage.tsx`, `Frontend/src/components/feed/PollPreview.tsx`, `Frontend/src/components/feed/PollModal.tsx`, `Frontend/src/pages/PollDetailPage.tsx`
  - **Voltooid**: 2025-01-28
  - **Uitgevoerd**: 
    - Poll preview component met getPoll() API
    - Poll modal met Dialog basis
    - Poll detail page en route `/polls/:id`
    - Note preview met truncate naar 150 chars
    - Location names altijd clickable
    - Reaction links clickable

- [x] **TASK-5.3**: Emoji reactions (activity reactions) ✅
  - **Beschrijving**: Vervang like button met emoji reactions set
  - **Bestanden**: `Infra/supabase/057_activity_reactions.sql`, `Backend/api/routers/activity.py`, `Frontend/src/lib/api.ts`, `Frontend/src/components/feed/EmojiReactions.tsx`, `Frontend/src/components/feed/FeedCard.tsx`
  - **Voltooid**: 2025-01-28
  - **Uitgevoerd**:
    - Database migratie 057: activity_reactions tabel
    - Backend API endpoints: POST/GET /activity/:id/reactions
    - Frontend API functies: toggleActivityReaction(), getActivityReactions()
    - EmojiReactions component met 6 emoji's (fire, heart, thumbs_up, smile, star, flag)
    - Like button vervangen met EmojiReactions component
    - ActivityItem type bijgewerkt met reactions en user_reaction velden

- [x] **TASK-5.4**: Media/images enhancement ✅
  - **Beschrijving**: Image display met aspect ratio, lazy loading, image modal
  - **Bestanden**: `Frontend/src/components/feed/FeedCard.tsx`, `Frontend/src/components/feed/ImageModal.tsx`
  - **Voltooid**: 2025-01-28
  - **Uitgevoerd**:
    - Image display: aspect ratio 16:9, max height 400px, lazy loading
    - ImageModal component met Dialog basis, full-size view, keyboard support
    - Clickable images open modal

### 🔴 To Do (Volgende stappen)

#### Fase 6: Testing & Refinement

- [x] **TASK-5.1**: Like functionaliteit implementeren ✅ (Voltooid in Fase 4, vervangen door emoji reactions in Fase 5)
  - **Beschrijving**: Like/unlike actions met API calls in FeedCard component
  - **Bestanden**: `Frontend/src/components/feed/FeedCard.tsx`
  - **Backend Status**: ✅ API endpoint beschikbaar (`toggleActivityLike`)
  - **Features**: 
    - Toggle like on click (gebruik `toggleActivityLike` API functie)
    - Optimistic updates
    - Error handling en rollback
    - Loading states
  - **Geschatte tijd**: 2-3 uur
  - **Voltooid**: 2025-01-28 (in Fase 4)
  - **Uitgevoerd**:
    - Like toggle geïntegreerd in FeedCard
    - Optimistic updates geïmplementeerd
    - Error handling met toast notifications
    - Rollback bij errors

- [x] **TASK-5.2**: Bookmark functionaliteit implementeren ✅ (Voltooid in Fase 4)
  - **Beschrijving**: Bookmark/unbookmark actions met API calls in FeedCard component
  - **Bestanden**: `Frontend/src/components/feed/FeedCard.tsx`
  - **Backend Status**: ✅ API endpoint beschikbaar (`toggleActivityBookmark`)
  - **Features**: 
    - Toggle bookmark on click (gebruik `toggleActivityBookmark` API functie)
    - Optimistic updates
    - Error handling
  - **Geschatte tijd**: 2-3 uur
  - **Voltooid**: 2025-01-28 (in Fase 4)
  - **Uitgevoerd**:
    - Bookmark toggle geïntegreerd in FeedCard
    - Optimistic updates geïmplementeerd
    - Error handling met toast notifications

- [x] **TASK-5.3**: Media display en handling ✅ (Voltooid in Fase 3)
  - **Beschrijving**: Images tonen in FeedCards
  - **Bestanden**: `Frontend/src/components/feed/FeedCard.tsx`
  - **Features**: 
    - Image loading states
    - Error handling voor broken images
    - Optional lazy loading
    - Full-width binnen card
  - **Geschatte tijd**: 2-3 uur
  - **Voltooid**: 2025-01-28 (in Fase 3)
  - **Uitgevoerd**:
    - Image display in FeedCard met error handling
    - Full-width images binnen card
    - Error handling voor broken images (hide on error)
    - Max height constraint voor images

- [ ] **TASK-5.4**: Mobile optimization & safe-area
  - **Beschrijving**: Mobile-first responsive design en safe-area support
  - **Bestanden**: Alle feed componenten
  - **Features**: 
    - Safe-area insets voor iOS
    - Touch targets minimaal 44x44px
    - Responsive spacing
    - Mobile breakpoint optimizations
  - **Geschatte tijd**: 2-3 uur
  - **Comments**: 
    - Test op verschillende devices
    - Check Tailwind safe-area utilities

#### Fase 6: Testing & Refinement
- [ ] **TASK-6.1**: Unit tests voor nieuwe componenten
  - **Beschrijving**: Tests voor alle nieuwe componenten
  - **Bestanden**: `Frontend/src/components/feed/**/*.spec.tsx`
  - **Coverage**: AppHeader, GreetingBlock, SearchInput, FeedFilterTabs, FeedCard, EventBadge
  - **Geschatte tijd**: 3-4 uur
  - **Comments**: 
    - Gebruik bestaande test patterns

- [ ] **TASK-6.2**: Integration tests voor FeedPage
  - **Beschrijving**: End-to-end flow tests
  - **Bestanden**: `Frontend/src/pages/__tests__/FeedPage.spec.tsx`
  - **Scenarios**: 
    - Loading states
    - Error handling
    - Filter changes
    - Search functionality
    - Like/bookmark toggles
  - **Geschatte tijd**: 2-3 uur
  - **Comments**: 
    - Mock API responses

- [ ] **TASK-6.3**: Performance optimization
  - **Beschrijving**: Performance checks en optimalisaties
  - **Bestanden**: FeedPage en componenten
  - **Optimalisaties**: 
    - Virtual scrolling indien nodig (>100 items)
    - Memoization van componenten
    - Lazy loading van images
    - Debounced search
  - **Geschatte tijd**: 2-3 uur
  - **Comments**: 
    - Profile met React DevTools
    - Check bundle size

- [ ] **TASK-6.4**: Accessibility improvements
  - **Beschrijving**: ARIA labels, keyboard navigation, screen reader support
  - **Bestanden**: Alle feed componenten
  - **Features**: 
    - ARIA labels voor interactive elements
    - Keyboard navigation (Tab, Enter, Space)
    - Focus management
    - Screen reader announcements
  - **Geschatte tijd**: 2-3 uur
  - **Comments**: 
    - Test met screen reader
    - Check WCAG compliance

---

### 🟡 In Progress (Momenteel bezig)

_Fase 1, 2, 3 en 4 zijn voltooid. Klaar voor Fase 5 (Polish) en Fase 6 (Testing)_

---

### ✅ Done (Afgerond)

**Fase 1: Backend API Uitbreidingen** (Voltooid: 2025-01-27)
- Alle 6 taken voltooid
- 4 database migraties uitgevoerd
- Backend API volledig uitgebreid
- Frontend TypeScript types bijgewerkt

**Fase 2: Nieuwe UI Componenten** (Voltooid: 2025-01-27)
- Alle 5 componenten geïmplementeerd (AppHeader, GreetingBlock, SearchInput, FeedFilterTabs, EventBadge)
- User Profile API functie toegevoegd (`getCurrentUser()`)
- Alle componenten mobile-first en responsive
- Componenten klaar voor integratie in Fase 4

**Fase 3: FeedCard Herontwerp** (Voltooid: 2025-01-28)
- FeedCard component volledig geïmplementeerd met user avatars, likes, bookmarks, media
- FeedList component geïmplementeerd met loading/empty states en pagination
- Beide componenten mobile-first en responsive
- TypeScript types volledig gedefinieerd

**Fase 4: FeedPage Herontwerp** (Voltooid: 2025-01-28)
- FeedPage volledig herontworpen naar mobile-first landing page
- Alle componenten geïntegreerd (AppHeader, GreetingBlock, SearchInput, FeedFilterTabs, FeedList)
- Data transformatie en API integratie compleet
- Search functionaliteit met debounce
- User data fetching voor personalized greeting
- Like en bookmark functionaliteit met optimistic updates
- Pagination en error handling volledig geïmplementeerd

**Fase 5: Functionaliteit & Polish** (Voltooid: 2025-01-28)
- Relative time formatting (< 24h: minuten/uren, >= 24h: exacte datum)
- Clickable content: poll preview, note preview, location links, reaction links
- Poll modal en detail page met route `/polls/:id`
- Emoji reactions: activity_reactions tabel, API endpoints, EmojiReactions component
- Like button vervangen met emoji reactions
- Media/images: aspect ratio 16:9, lazy loading, ImageModal component

---

## 📝 Aantekeningen

### Design Decisions
- **Logo**: Gebruik bestaand Komşu logo/wordmark indien beschikbaar
- **Colors**: Gebruik bestaand brand color systeem voor accenten
- **Icons**: Gebruik lucide-react icon library (al in gebruik)
- **Search**: Start met client-side filtering, API search later als nodig

### Technische Overwegingen
- **State Management**: React hooks (useState, useEffect) voor FeedPage state
- **API Calls**: Bestaand apiFetch pattern gebruiken
- **Error Handling**: Toast notifications via sonner (al in gebruik)
- **Loading States**: Skeleton loaders waar mogelijk
- **Type Safety**: Volledige TypeScript coverage voor alle nieuwe componenten

### Dependencies
- Geen nieuwe dependencies verwacht
- Bestaande libraries:
  - React + TypeScript
  - Tailwind CSS
  - lucide-react (icons)
  - sonner (toasts)

### Open Questions
- [ ] Bestaat er al een notification systeem/endpoint voor de bell icon?
- [ ] Wat is de exacte branding/logo asset die gebruikt moet worden?
- [x] ~~Moeten bookmarks persistent zijn (localStorage) of alleen server-side?~~ → **Besloten**: Server-side (activity_bookmarks tabel), consistent met likes
- [ ] Zijn er performance requirements voor initial load?

### Blockers
_Geen blockers op dit moment_

---

## 🎯 Definition of Done

Een taak is afgerond wanneer:
- [ ] Code is geschreven en werkt lokaal
- [ ] TypeScript types zijn correct gedefinieerd
- [ ] Component is responsive (mobile + desktop)
- [ ] Accessibility is gecheckt (keyboard nav, ARIA)
- [ ] Code is gereviewd (zelf review of met team)
- [ ] Tests zijn geschreven en passing (indien van toepassing)
- [ ] Geen console errors of warnings
- [ ] Documentatie/aantekeningen zijn bijgewerkt

---

## 📚 Referenties

- **FeedPage (Herontworpen)**: `Frontend/src/pages/FeedPage.tsx` ✅
- **FeedCard Component**: `Frontend/src/components/feed/FeedCard.tsx` ✅
- **FeedList Component**: `Frontend/src/components/feed/FeedList.tsx` ✅
- **AppHeader Component**: `Frontend/src/components/feed/AppHeader.tsx` ✅
- **GreetingBlock Component**: `Frontend/src/components/feed/GreetingBlock.tsx` ✅
- **SearchInput Component**: `Frontend/src/components/feed/SearchInput.tsx` ✅
- **FeedFilterTabs Component**: `Frontend/src/components/feed/FeedFilterTabs.tsx` ✅
- **EventBadge Component**: `Frontend/src/components/feed/EventBadge.tsx` ✅
- **Huidige ActivityCard (Legacy)**: `Frontend/src/components/feed/ActivityCard.tsx` (nog beschikbaar voor referentie)
- **Activity Feed API**: `Backend/api/routers/activity.py` (bijgewerkt met user info, likes, bookmarks, media)
- **ActivityItem Type**: `Frontend/src/lib/api.ts` (line 875+) - bijgewerkt met alle nieuwe velden
- **Bestaand FooterTabs**: `Frontend/src/components/FooterTabs.tsx`
- **Bestaand News Bookmarks Pattern**: `Frontend/src/hooks/useNewsBookmarks.ts`
- **User Profiles API**: `Backend/api/routers/profiles.py` - nieuwe `/me` endpoint toegevoegd
- **Database Migraties**: 
  - `Infra/supabase/053_add_event_activity_type.sql` ✅
  - `Infra/supabase/054_add_media_url_to_activity_stream.sql` ✅
  - `Infra/supabase/055_activity_likes.sql` ✅
  - `Infra/supabase/056_activity_bookmarks.sql` ✅

---

**Laatste update**: 2025-01-28  
**Gewijzigd door**: AI Assistant  
**Fase 2 Voltooid**: 2025-01-27  
**Fase 3 Voltooid**: 2025-01-28  
**Fase 4 Voltooid**: 2025-01-28

---

## 📊 Voortgang Status

### Fase 1: Backend API Uitbreidingen ✅ VOLTOOID (2025-01-27)

**Uitgevoerde werkzaamheden**:
1. ✅ Database migraties (053-056) - Alle 4 migraties succesvol uitgevoerd
2. ✅ Activity Stream API uitgebreid met:
   - User info (JOIN met user_profiles)
   - Media URL ondersteuning
   - Event type support
   - Like functionaliteit (count + toggle)
   - Bookmark functionaliteit (status + toggle)
3. ✅ User Profile endpoint `/api/v1/users/me` toegevoegd
4. ✅ Frontend TypeScript types volledig bijgewerkt

**Nieuwe API Endpoints**:
- `POST /api/v1/activity/{id}/like` - Toggle like op activity item
- `POST /api/v1/activity/{id}/bookmark` - Toggle bookmark op activity item  
- `GET /api/v1/users/me` - Haal huidige user profile op (retourneert None voor anonymous)

**Nieuwe Database Tabellen**:
- `activity_likes` - Voor like tracking per user/client
- `activity_bookmarks` - Voor bookmark tracking per user/client

**Bijgewerkte Database Schema**:
- `activity_stream` - media_url kolom toegevoegd, event type toegevoegd aan constraint

**Klaar voor**: Fase 2 (Nieuwe UI Componenten) kan nu starten met alle backend support beschikbaar.

---

### Fase 2: Nieuwe UI Componenten ✅ VOLTOOID (2025-01-27)

**Uitgevoerde werkzaamheden**:
1. ✅ AppHeader component geïmplementeerd
   - Logo "Komşu" links, notification bell rechts
   - Safe-area support, mobile-first design
2. ✅ GreetingBlock component geïmplementeerd
   - Time-based greeting (Good Morning/Afternoon/Evening)
   - User name display met brand color accent
   - Fallback voor anonymous users
3. ✅ SearchInput component geïmplementeerd
   - Fully rounded search input met icon
   - Gebaseerd op bestaand Input component
4. ✅ FeedFilterTabs component geïmplementeerd
   - Horizontaal scrollbare filter pills
   - Active/inactive states met visueel onderscheid
   - 8 filters: All, Check-ins, Events, Reactions, Notes, Polls, Favorites, Bulletin
5. ✅ EventBadge component geïmplementeerd
   - Rode pill badge voor event items
   - Absolute positioning voor overlay
6. ✅ User Profile API functie toegevoegd
   - `getCurrentUser()` functie in `lib/api.ts`
   - Error handling voor anonymous users

**Nieuwe Componenten**:
- `Frontend/src/components/feed/AppHeader.tsx`
- `Frontend/src/components/feed/GreetingBlock.tsx`
- `Frontend/src/components/feed/SearchInput.tsx`
- `Frontend/src/components/feed/FeedFilterTabs.tsx`
- `Frontend/src/components/feed/EventBadge.tsx`

**Nieuwe API Functies**:
- `getCurrentUser()` - Haal huidige user profile op (frontend)

**Extra Wijzigingen**:
- CSS utility toegevoegd aan `index.css` voor scrollbar hiding op horizontaal scrollbare elementen

**Klaar voor**: Fase 3 (FeedCard Herontwerp) kan nu starten met alle UI building blocks beschikbaar.

---

### Fase 3: FeedCard Herontwerp ✅ VOLTOOID (2025-01-28)

**Uitgevoerde werkzaamheden**:
1. ✅ FeedCard component geïmplementeerd
   - User avatar met fallback naar initialen
   - Like en bookmark functionaliteit
   - Media image support met error handling
   - EventBadge overlay voor event items
   - Responsive design met proper spacing
   - Timestamp formatting
   - Click navigation voor location detail en bulletin posts
2. ✅ FeedList component geïmplementeerd
   - Container met spacing tussen cards
   - Loading states met skeleton loaders
   - Empty states met custom messages
   - Pagination met "Meer laden" button
   - Error handling

**Nieuwe Componenten**:
- `Frontend/src/components/feed/FeedCard.tsx`
- `Frontend/src/components/feed/FeedList.tsx`

**Klaar voor**: Fase 4 (FeedPage Herontwerp) kan nu starten met alle componenten beschikbaar.

---

### Fase 4: FeedPage Herontwerp ✅ VOLTOOID (2025-01-28)

**Uitgevoerde werkzaamheden**:
1. ✅ FeedPage volledig herontworpen
   - Verwijderd: Tabs, PageShell, nested structure
   - Nieuwe layout: AppHeader, GreetingBlock, SearchInput, FeedFilterTabs, FeedList, FooterTabs
   - Mobile-first verticale scrollbare layout
   - State management voor alle features
2. ✅ Data transformatie geïmplementeerd
   - `transformActivityItem()` helper functie
   - Integratie met `getActivityFeed()` API
   - Pagination met `handleLoadMore()`
   - Hergebruik van `getActivityMessage()` logica
3. ✅ Search functionaliteit geïmplementeerd
   - Client-side filtering met 300ms debounce
   - Search in location name, user name, en content text
   - Combineert met filter tabs (API filter + client-side search)
   - Empty state messages voor search results
4. ✅ User data fetching geïmplementeerd
   - `getCurrentUser()` call op component mount
   - Silent error handling voor anonymous users
   - User name geïntegreerd in GreetingBlock
5. ✅ Like en bookmark functionaliteit geïntegreerd
   - Optimistic updates
   - Error handling met toast notifications
   - Rollback bij errors

**Gewijzigde Bestanden**:
- `Frontend/src/pages/FeedPage.tsx` - Volledig herontworpen

**Klaar voor**: Fase 5 (Polish) en Fase 6 (Testing) kunnen nu starten.

---

## 🔄 Huidige Status & Volgende Stappen

**Huidige Fase**: Fase 1, 2, 3 en 4 voltooid ✅  
**Volgende Fase**: Fase 5 - Functionaliteit & Polish, Fase 6 - Testing & Refinement  

**Aanbevolen startpunt voor volgende sessie**:
1. Fase 5.4: Mobile optimization & safe-area (als nog nodig)
2. Fase 6.1: Unit tests voor nieuwe componenten
3. Fase 6.2: Integration tests voor FeedPage
4. Fase 6.3: Performance optimization
5. Fase 6.4: Accessibility improvements

**Belangrijke notities voor volgende sessie**:
- Alle core functionaliteit is geïmplementeerd en werkend
- FeedPage is volledig functioneel als mobile-first landing page
- Like en bookmark functionaliteit zijn al geïntegreerd
- Media display is geïmplementeerd
- Focus kan nu liggen op testing, performance en accessibility




