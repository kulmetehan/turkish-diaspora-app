---
title: Testing Strategy - Identity & Activity Layer
status: active
scope: testing
---

# Testing Strategy for Identity & Activity Layer

## Overview

Comprehensive testing strategy covering unit tests, integration tests, E2E tests, and load tests for the Identity & Activity Layer features.

## Test Structure

```
Backend/tests/
├── unit/
│   ├── test_trending_algorithm.py
│   ├── test_xp_streak_logic.py
│   └── test_rate_limiting.py
├── integration/
│   ├── test_check_in_flow.py
│   └── test_activity_stream_worker.py
└── fixtures/
    └── __init__.py (factory functions)
```

## Unit Tests

### Trending Algorithm (`test_trending_algorithm.py`)
- Test decay formula with various age_hours values
- Test ranking order with different activity counts
- Test edge cases (zero activity, very old activity)
- Verify exponential decay behavior

### XP & Streak Logic (`test_xp_streak_logic.py`)
- Test XP awards per action type
- Test daily XP cap enforcement
- Test streak increment/reset logic (36h window)
- Test badge awarding conditions

### Rate Limiting (`test_rate_limiting.py`)
- Test sliding window calculation
- Test per-action limits
- Test cleanup of old records

## Integration Tests

### Check-in Flow (`test_check_in_flow.py`)
1. Create check-in → verify in check_ins table
2. Wait for activity_stream worker → verify in activity_stream
3. Verify XP awarded (if gamification enabled)
4. Verify rate limiting prevents duplicates

### Activity Stream Worker (`test_activity_stream_worker.py`)
1. Create multiple activities (check-ins, reactions, notes)
2. Run worker → verify all processed
3. Verify processed_in_activity_stream flags set
4. Test rebuild mode

## E2E Tests

### Anonymous User Flow
1. Generate client_id in frontend
2. Create check-in with client_id
3. View own activity feed
4. Create account → verify migration of activity

### Auth Migration Flow
1. Create activities as anonymous (client_id)
2. Sign up → verify activities migrated to user_id
3. Verify XP/streaks preserved

## Load Tests

### Scenario: Check-in Storm
- 1000 concurrent users
- Each performs 10 check-ins
- Measure: Response times, DB load, worker lag

### Scenario: Poll Voting
- 5000 users vote on same poll
- Measure: Rate limiting effectiveness, DB performance

## Test Fixtures

Factory functions in `Backend/tests/fixtures/__init__.py`:
- `make_location()`: Create test location dict
- `make_user()`: Create test user dict
- `make_check_in()`: Create test check-in dict
- `make_poll_with_options()`: Create test poll with options
- `make_activity_stream_entry()`: Create test activity stream entry

## Seed Script

`Backend/scripts/seed_dev_data.py`:
- Creates test users, cities, locations
- Generates random activity (check-ins, reactions, notes)
- Creates sample polls with responses
- Sets up trending data for testing

## Running Tests

```bash
# Unit tests
pytest Backend/tests/unit/

# Integration tests
pytest Backend/tests/integration/

# All tests
pytest Backend/tests/

# With coverage
pytest Backend/tests/ --cov=Backend/app --cov=Backend/api
```

## Test Database Setup

Tests should use a separate test database or in-memory database to avoid affecting development data.

## Continuous Integration

All tests should run in CI/CD pipeline:
- On every pull request
- Before merging to main
- On scheduled basis (nightly)



























