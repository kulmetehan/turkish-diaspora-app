# Turkish Diaspora App - Project Context

## Project Overview

The Turkish Diaspora App (TDA) is an AI-driven location discovery and mapping application designed to help Turkish communities in the Netherlands find relevant businesses and services. The application automatically discovers, validates, and displays Turkish-oriented businesses using AI classification and multiple data sources.

## Architecture Overview

### System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Database     │
│   (React/TS)    │◄──►│   (FastAPI)     │◄──►│   (Supabase)   │
│                 │    │                 │    │   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Map Services  │    │   AI Services   │    │   Audit Logs    │
│ (Leaflet/Mapbox)│    │   (OpenAI)      │    │   (AI Logs)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│  Discovery APIs │    │  Classification  │
│ (OSM/Google)    │    │   & Validation   │
└─────────────────┘    └─────────────────┘
```

### Data Flow Diagram
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Discovery     │    │   Classification│    │   Verification │
│   Bot           │───►│   Service       │───►│   Bot           │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CANDIDATE     │    │   AI Analysis   │    │   VERIFIED     │
│   Locations     │    │   & Scoring     │    │   Locations    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OSM/Google   │    │   OpenAI API    │    │   Frontend      │
│   APIs          │    │   Integration   │    │   Display       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Technology Stack

### Backend (Python/FastAPI)
- **Framework**: FastAPI with async/await patterns
- **Database**: Supabase (PostgreSQL) with async connection pooling
- **AI Integration**: OpenAI API for classification and validation
- **Discovery APIs**: OSM Overpass API + Google Places API
- **Logging**: Structured logging with request ID tracking
- **Workers**: Background tasks for discovery and verification

### Frontend (React/TypeScript)
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite for fast development and building
- **Styling**: Tailwind CSS with component-based design
- **Maps**: Leaflet/Mapbox integration for location visualization
- **State Management**: React hooks (useState, useEffect, useMemo)
- **UI Components**: Radix UI primitives with custom styling

### Infrastructure
- **Database**: Supabase (PostgreSQL) with real-time capabilities
- **Deployment**: GitHub Pages for frontend, Heroku/Railway for backend
- **Monitoring**: Built-in metrics and audit logging
- **Configuration**: YAML-based category and city mappings

## Current Status

### Completed Features
- ✅ **OSM Discovery Pipeline**: Production-ready discovery system for Rotterdam
- ✅ **AI Classification**: Automated Turkish business identification
- ✅ **Verification Pipeline**: CANDIDATE → VERIFIED state promotion
- ✅ **Frontend Interface**: React-based location browser with map integration
- ✅ **Category System**: 8 main business categories with Turkish aliases
- ✅ **Error Handling**: Robust error handling and recovery mechanisms
- ✅ **Rate Limiting**: Respectful API usage with backoff strategies

### Recent Work (October 2025)
- **Rotterdam Production Rollout**: Successfully discovered 151+ Turkish businesses
- **VerifyLocationsBot**: Implemented automated verification pipeline
- **Enhanced Error Handling**: Improved OSM API error handling and endpoint rotation
- **Category Mapping**: Enhanced Turkish business category detection
- **Performance Optimization**: Improved database connection pooling

### Current Phase: TDA-107 (Consolidation)
- **Focus**: Consolidating discovery pipeline and verification system
- **Next Cities**: The Hague, Amsterdam, Utrecht
- **Improvements**: Enhanced monitoring, automated health checks
- **Optimization**: Database pool tuning, sequential chunk execution

## Business Categories

The application focuses on 8 main categories of Turkish-oriented businesses:

1. **Restaurant** - Turkish restaurants and eateries
2. **Bakery** - Turkish bakeries and patisseries
3. **Supermarket** - Turkish markets and grocery stores
4. **Barber** - Turkish barbershops and hair salons
5. **Mosque** - Turkish community mosques
6. **Travel Agency** - Turkish travel agencies
7. **Butcher** - Turkish butchers and meat shops
8. **Fast Food** - Turkish fast food establishments

Each category includes Turkish aliases and OSM tag mappings for accurate discovery.

## Development Environment

### Backend Setup
```bash
cd Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd Frontend
npm install
npm run dev
```

### Database Setup
- Supabase project with PostgreSQL
- Environment variables in `.env` files
- Database migrations in `/Infra/supabase/`

## Key Files and Directories

### Backend Structure
- `app/main.py` - FastAPI application entry point
- `app/workers/` - Discovery and verification bots
- `app/services/` - Core business logic (AI, OSM, Google)
- `api/routers/` - FastAPI endpoints
- `app/core/` - Logging and request ID management

### Frontend Structure
- `src/App.tsx` - Main React application
- `src/components/` - UI components (Filters, MapView, LocationList)
- `src/lib/` - Utilities, API clients, map integration
- `src/hooks/` - Custom React hooks

### Configuration
- `Infra/config/categories.yml` - Business category mappings
- `Infra/config/cities.yml` - City and district configurations
- `Backend/requirements.txt` - Python dependencies
- `Frontend/package.json` - Node.js dependencies

## AI Integration

### Classification Service
- Uses OpenAI API for location classification
- Supports Turkish business detection
- Confidence scoring for classification results
- Validation of classification payloads

### Verification Pipeline
- Automated CANDIDATE → VERIFIED promotion
- AI-based validation of discovered locations
- Audit logging for all AI operations
- Configurable confidence thresholds

### Discovery Process
1. **Grid-based Discovery**: Systematic coverage of target areas
2. **Multi-source Data**: OSM Overpass + Google Places API
3. **AI Classification**: Automated Turkish business identification
4. **Verification**: AI validation and state promotion
5. **Audit Trail**: Complete logging of all operations

## Monitoring and Metrics

### Database Monitoring
- Connection pool status
- Query performance metrics
- Insert velocity tracking
- Error rate monitoring

### API Monitoring
- Overpass API success rates
- Response time tracking
- Endpoint rotation effectiveness
- Rate limiting compliance

### AI Operations
- Classification accuracy
- Verification success rates
- Confidence score distributions
- Audit trail completeness

## Next Steps

### Immediate Priorities
1. **The Hague Discovery**: Next city rollout
2. **Database Optimization**: Connection pool tuning
3. **Enhanced Monitoring**: Real-time dashboard
4. **Automated Health Checks**: Overpass endpoint monitoring

### Future Enhancements
1. **Amsterdam Rollout**: Major metropolitan area
2. **Utrecht Discovery**: Growing Turkish community
3. **User Interface**: Enhanced filtering and search
4. **Mobile Optimization**: Responsive design improvements

## Development Guidelines

### Code Standards
- **Python**: Async/await patterns, type hints, structured logging
- **TypeScript**: Strict mode, React hooks, component-based design
- **Database**: Async operations, connection pooling, audit trails
- **AI**: Proper error handling, confidence scoring, validation

### Testing Strategy
- **Unit Tests**: Core business logic testing
- **Integration Tests**: API endpoint testing
- **End-to-End Tests**: Full pipeline testing
- **Performance Tests**: Load and stress testing

### Deployment
- **Frontend**: GitHub Pages with Vite build
- **Backend**: Heroku/Railway with environment variables
- **Database**: Supabase with automated backups
- **Monitoring**: Built-in metrics and alerting

This project represents a comprehensive solution for Turkish diaspora community mapping, combining modern web technologies with AI-powered discovery and verification systems.
