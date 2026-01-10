# Chat Preview Implementation Status

**Laatste update**: 2025-01-27 (Fixes geïmplementeerd)

## Overzicht

Chat previews tonen een preview van het onderwerp bovenaan elke chat. Dit zijn klikbare previews die gebruikers doorlinken naar de bron content (nieuws, events, feed items, muziek).

## Huidige Implementatie

### ✅ Werkende Features

1. **News Previews**: Volledig werkend
   - Preview wordt getoond met title, description, image
   - Klikbaar en opent nieuws URL in nieuwe tab
   - Redundante topic header wordt verborgen voor news chats

2. **Event Previews**: Volledig werkend
   - Preview wordt getoond met title, description, image
   - Klikbaar en navigeert naar events page met detail overlay

3. **Check-in Previews**: Volledig werkend
   - Preview wordt getoond met location name als title
   - Klikbaar en navigeert naar location detail page (`/locations/{location_id}`)
   - Geen icon/label voor feed items

4. **Feed Item Navigatie**: 
   - Check-ins navigeren naar location detail
   - Andere feed items navigeren naar feed page

### ✅ Oplossingen Geïmplementeerd

#### Poll Previews (2025-01-27)
- ✅ Activity stream entries worden nu automatisch aangemaakt bij poll creation
- ✅ Backend poll detection fallback toegevoegd voor bestaande polls (checkt direct polls table)
- ✅ Migratie script voor backfill bestaande polls zonder activity_stream entries
- ✅ Debug logging toegevoegd voor troubleshooting
- ✅ Polls worden nu correct getoond met PollPreview component
- ✅ Polls linken niet meer naar locaties (location_id wordt correct uitgesloten)
- ✅ **ID Collision Fix**: Backend checkt EERST of content_id een poll_id is voordat het naar activity_stream.id kijkt, voorkomt collision met check_ins of andere activities met dezelfde ID

#### Music Previews (2025-01-27)
- ✅ URL veld toegevoegd aan chat_topics tabel voor directe opslag
- ✅ URL wordt nu automatisch geparsed en opgeslagen in topic.url veld bij topic creation
- ✅ Verbeterde URL extractie met meerdere fallback strategieën:
  1. Eerst check topic.url veld (meest betrouwbaar)
  2. Dan description parsing met regex
  3. Als laatste fallback naar news feed API
- ✅ Backend gebruikt nu topic.url veld als primaire bron voor URL retrieval

### ✅ Laatste Fix: Poll ID Collision (2025-01-27)

**Probleem**: Poll chats toonden nog steeds een locatie in plaats van de poll zelf.

**Root Cause**: Backend checkte eerst `WHERE ast.id = content_id`. Als `content_id` een poll_id was (bijvoorbeeld 5) en er bestond ook een activity_stream entry met id=5 (bijvoorbeeld een check_in), dan werd die check_in gevonden en gebruikt, resulterend in het tonen van een locatie.

**Fix**: Backend checkt nu EERST of `content_id` een poll_id is (polls table) VOORDAT het naar activity_stream.id kijkt. Als het een poll is, return direct met `location_id=None` om ID collision te voorkomen.

**Implementatie**: 
- Feed content_type handling herschreven om poll_id check als eerste prioriteit te geven
- Activity_stream.id lookup wordt alleen gebruikt voor non-poll feed items
- Polls hebben altijd `location_id=None` om locatie links te voorkomen

### ⚠️ Bekende Problemen

Geen bekende problemen meer - alle issues zijn opgelost.

## Technische Details

### Backend (`Backend/api/routers/chat.py`)

**Endpoint**: `GET /api/v1/chat/topics/{topic_id}/content-item`

**Response Model**: `ContentItemPreview`
```python
class ContentItemPreview(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None
    content_type: str  # 'news', 'event', 'feed', 'music'
    activity_type: Optional[str] = None  # For feed items
    poll_id: Optional[int] = None  # For poll activities
    location_id: Optional[int] = None  # For check_in activities
```

**Content Type Handling**:
- **news**: Haalt data uit `raw_ingested_news` table
- **music**: Fallback naar topic data als niet in database, met URL retrieval uit `topic.url` veld (primair), description parsing (fallback), of news feed API (laatste fallback)
- **event**: Haalt data uit `events_public` view
- **feed**: 
  - Haalt data uit `activity_stream` table
  - Speciale handling voor polls: 
    1. Zoekt eerst naar `activity_stream` item met `activity_type='poll'` en `payload->>'poll_id' = content_id`
    2. Als niet gevonden, checkt direct polls table (fallback voor bestaande polls zonder activity_stream entry)
  - `location_id` wordt uitgesloten voor polls (zodat ze niet naar locaties linken)

### Frontend (`Frontend/src/components/chat/ChatItemPreview.tsx`)

**Component Logica**:
1. Laadt `ContentItemPreview` via API
2. Detecteert polls: `content_type === "feed" && activity_type in ("poll", "poll_response") && poll_id`
3. Voor polls: toont `PollPreview` component
4. Voor andere items: toont reguliere preview met title, description, image
5. Navigatie:
   - **news/music**: opent URL in nieuwe tab
   - **event**: navigeert naar `/events` met `detailId`
   - **feed check_in**: navigeert naar `/locations/{location_id}`
   - **feed polls**: geen navigatie (handled door PollPreview)
   - **feed other**: navigeert naar `/feed`

**Styling**:
- Feed items hebben geen icon/label
- Alleen non-poll feed items tonen "Bekijk origineel" link
- News/event/music items tonen "Bekijk origineel" met external link icon

### Chat Topic Creation

**Voor Polls** (`Frontend/src/components/feed/PollPreview.tsx`):
```tsx
<ChatButton
  contentType="feed"
  contentId={pollId}  // ⚠️ Dit is poll_id, niet activity_stream.id
  title={poll.title}
  description={poll.question || undefined}
/>
```

**Voor Music** (`Frontend/src/components/news/NewsCard.tsx`):
```tsx
<ChatButton
  contentType="music"
  contentId={item.id}  // derived_id (hash)
  title={item.title}
  description={isMusicTrack && item.url ? `${item.snippet || ""} ${item.url}`.trim() : (item.snippet || undefined)}
/>
```

## Geïmplementeerde Fixes

### Poll Activity Stream Creation
- **Fix**: Activity stream entries worden nu automatisch aangemaakt bij poll creation in `Backend/api/routers/admin_polls.py`
- **Implementatie**: Gebruikt 'business' actor_type met system UUID (`00000000-0000-0000-0000-000000000000`) voor admin-created polls
- **Backfill**: Migratie script `Backend/scripts/backfill_poll_activity_stream.py` voor bestaande polls
- **Fallback**: Backend checkt direct polls table als activity_stream entry niet gevonden wordt

### Music URL Storage
- **Fix**: URL veld toegevoegd aan `chat_topics` tabel via migratie `106_add_chat_topics_url.sql`
- **Implementatie**: Backend parst URL uit description en slaat op in `topic.url` veld bij topic creation
- **Retrieval**: Backend gebruikt `topic.url` als primaire bron, met fallback naar description parsing en news feed API

### Debug Logging
- **Fix**: Debug logging toegevoegd aan `get_content_item_for_preview` endpoint voor troubleshooting
- **Locaties**: 
  - Bij start van endpoint (topic_id, content_type, content_id)
  - Bij activity_stream lookup failures
  - Bij poll fallback detection
  - Bij music URL retrieval

## Volgende Stappen (Monitoring)

1. **Monitor Chat Preview Success Rates**:
   - Check error logs voor content-item preview endpoint
   - Monitor debug logs voor poll/music detection rates

2. **Test Backfill Script**:
   - Run `Backend/scripts/backfill_poll_activity_stream.py` op staging/production
   - Verifieer dat alle bestaande polls activity_stream entries hebben

3. **Future Improvements**:
   - Overweeg om activity_stream entries automatisch te maken via database trigger
   - Voeg metrics toe voor chat preview success rates per content type
   - Overweeg om URL veld ook toe te voegen aan news items indien nodig

## Gerelateerde Bestanden

### Backend
- `Backend/api/routers/chat.py` - Content item preview endpoint (met poll fallback en music URL retrieval)
- `Backend/api/routers/admin_polls.py` - Poll creation met activity_stream entry creation
- `Backend/services/chat_service.py` - Chat service (URL parsing en opslag)
- `Backend/scripts/backfill_poll_activity_stream.py` - Backfill script voor bestaande polls

### Frontend
- `Frontend/src/components/chat/ChatItemPreview.tsx` - Preview component
- `Frontend/src/components/feed/PollPreview.tsx` - Poll preview component
- `Frontend/src/components/news/NewsCard.tsx` - News/music card met ChatButton
- `Frontend/src/lib/api.ts` - API client en types

### Database Migrations
- `Infra/supabase/106_add_chat_topics_url.sql` - Voegt url veld toe aan chat_topics
- `Infra/supabase/107_backfill_poll_activity_stream.sql` - Backfill activity_stream entries voor bestaande polls
