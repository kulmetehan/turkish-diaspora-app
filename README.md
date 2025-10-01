# Diaspora - Turkish & Dutch News Aggregator

A bilingual web application that aggregates news from Turkish and Dutch sources, making it easier for the Turkish diaspora in the Netherlands to stay informed.

## Live Demo

**Web App:** https://kulmetehan.github.io/diaspora-app/  
**API Documentation:** https://diaspora-backend-api.onrender.com/docs

## Features

- Real-time news aggregation from NOS.nl (Dutch) and TRT Haber (Turkish)
- Language filtering (Dutch/Turkish/All)
- Responsive design (works on desktop, tablet, mobile)
- Direct links to original articles
- Statistics dashboard
- Auto-refresh every 5 minutes

## Tech Stack

**Frontend:**
- HTML5, CSS3, JavaScript (ES6+)
- Pure vanilla JS (no frameworks)
- Hosted on GitHub Pages

**Backend:**
- Python 3.13
- FastAPI
- Supabase (PostgreSQL)
- RSS feed parsing (feedparser, BeautifulSoup)
- Hosted on Render

## Project Status

**Completed:**
- Epic 1: Content Foundation (Database, RSS feeds, API)
- Epic 2: Web Application Frontend (Basic MVP)

**In Progress:**
- Epic 3: AI Enhancement Pipeline (Summarization & Translation)

**Planned:**
- Sprint 4: Advanced filtering and analytics
- Sprint 5: User preferences and engagement
- Sprint 6: Music, Sports, and Events tabs

## Local Development

### Prerequisites
- Python 3.13+
- Modern web browser
- Supabase account

### Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Create .env file with:
# SUPABASE_URL=your_url
# SUPABASE_KEY=your_key

python3 api_server.py
Server runs at http://localhost:8000
Frontend
Simply open index.html in your browser
Current Statistics

72 articles in database
2 sources: NOS.nl (Dutch), TRT Haber (Turkish)
21 Dutch articles
51 Turkish articles

Deployment
Both frontend and backend deploy automatically on git push:

Frontend deploys to GitHub Pages
Backend deploys to Render

API Endpoints

GET / - Health check
GET /api/content/latest - Get articles (supports ?language=nl|tr, ?limit=1-100)
GET /api/content/{id} - Get specific article
GET /api/stats - Database statistics
GET /docs - Interactive API documentation

Roadmap
Next Features:

AI-powered article summarization
Dutch to Turkish translation
Location detection and tagging
Category filters (Politics, Sports, Economy)
User preference persistence
Music discovery (Spotify integration)
Local events calendar
Sports scores

License
MIT
Author
Metehan Kul
GitHub: @kulmetehan

Built as part of a 12-week MVP development plan for the Turkish diaspora community.
