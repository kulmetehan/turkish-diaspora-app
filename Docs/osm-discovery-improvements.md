# OSM Discovery Pipeline Improvements

## Overview

This document describes the comprehensive improvements made to the OSM discovery pipeline to ensure full compliance with Overpass API policies while maximizing data coverage and reliability.

## Key Improvements

### 1. Overpass API Policy Compliance
- **User-Agent**: Proper identification with `TurkishDiasporaApp/1.0 (contact: m.kul@lamarka.nl)`
- **Rate Limiting**: Configurable QPS with jitter to avoid overwhelming servers
- **Endpoint Rotation**: Automatic failover across multiple Overpass endpoints
- **Backoff Strategy**: Exponential backoff with configurable series
- **Read-Only**: No edit API usage, only discovery queries

### 2. Robust Error Handling
- **Endpoint Rotation**: Automatic switching on 429, 5xx, and timeout errors
- **Retry Logic**: Intelligent retry with exponential backoff
- **Telemetry**: Comprehensive logging of all API calls
- **Graceful Degradation**: Continues processing even when some calls fail

### 3. Adaptive Cell Subdivision
- **Quad-Tree Logic**: Automatically subdivides cells when results hit limits
- **Configurable Depth**: Maximum subdivision depth to prevent infinite recursion
- **Minimum Cell Size**: Prevents subdivision below 250m edge length
- **Duplicate Prevention**: Removes duplicate results across subdivided cells

### 4. Union Query Optimization
- **Multi-Category Queries**: Combines multiple categories in single API calls
- **Turkish Hints**: Optional filtering for Turkish-specific businesses
- **Efficient Filtering**: Uses OSM tag combinations for better coverage

### 5. Comprehensive Telemetry
- **Database Logging**: All API calls logged to `overpass_calls` table
- **Performance Metrics**: Response times, success rates, error patterns
- **Monitoring Queries**: Pre-built SQL queries for analysis
- **Cell Tracking**: Unique identifiers for subdivision tracking

## Configuration

### Environment Variables

```bash
# Data provider selection
DATA_PROVIDER=osm

# Overpass API configuration
OVERPASS_USER_AGENT=TurkishDiasporaApp/1.0 (contact: m.kul@lamarka.nl)
DISCOVERY_RATE_LIMIT_QPS=0.08
DISCOVERY_SLEEP_BASE_S=7.0
DISCOVERY_SLEEP_JITTER_PCT=0.40
DISCOVERY_BACKOFF_SERIES=20,60,180,420
OVERPASS_TIMEOUT_S=60
DISCOVERY_MAX_RESULTS=50

# Turkish hints filtering
OSM_TURKISH_HINTS=1

# Cell subdivision
MAX_SUBDIVIDE_DEPTH=2
```

### Category Configuration

The `categories.yml` file has been updated with:
- **Butcher category**: Added missing `butcher` category with proper OSM tags
- **OSM Tag Mapping**: Each category now has `osm_tags` configuration
- **Turkish Aliases**: Turkish language aliases for better discovery

## Usage Examples

### Basic OSM Discovery

```bash
export DATA_PROVIDER=osm
export OVERPASS_USER_AGENT="TurkishDiasporaApp/1.0 (contact: m.kul@lamarka.nl)"
export DISCOVERY_RATE_LIMIT_QPS=0.08
export DISCOVERY_SLEEP_BASE_S=7.0
export DISCOVERY_SLEEP_JITTER_PCT=0.40
export DISCOVERY_BACKOFF_SERIES=20,60,180,420
export OVERPASS_TIMEOUT_S=60
export DISCOVERY_MAX_RESULTS=50
export OSM_TURKISH_HINTS=1
export MAX_SUBDIVIDE_DEPTH=2

python -m app.workers.discovery_bot \
  --city rotterdam \
  --categories barber,butcher,bakery,supermarket,restaurant,fast_food,mosque,travel_agency \
  --nearby-radius-m 1300 \
  --grid-span-km 3.5 \
  --max-cells-per-category 18 \
  --max-total-inserts 220 \
  --inter-call-sleep-s 7.0 \
  --language nl \
  --chunks 3 \
  --chunk-index 0
```

### Chunked Processing

For large areas, use chunked processing:

```bash
# Chunk 0
python -m app.workers.discovery_bot --chunks 3 --chunk-index 0

# Chunk 1 (after a short pause)
python -m app.workers.discovery_bot --chunks 3 --chunk-index 1

# Chunk 2 (after a short pause)
python -m app.workers.discovery_bot --chunks 3 --chunk-index 2
```

## Monitoring and Analysis

### Database Schema

The `overpass_calls` table tracks:
- **Request Details**: Endpoint, query size, timeout settings
- **Response Metrics**: Status code, found count, normalized count
- **Performance**: Duration, attempt number, error messages
- **Geographic**: Cell ID, radius, coordinates
- **Categories**: Requested category sets

### Monitoring Queries

Use the queries in `Infra/monitoring/sql/monitoring.sql` for:

1. **Insert Rate Analysis**: Track discovery performance over time
2. **Capped Cell Detection**: Identify cells that need subdivision
3. **Error Analysis**: Monitor API errors and patterns
4. **Performance Metrics**: Response times and success rates
5. **Geographic Coverage**: Discovery effectiveness by region

### Key Metrics to Monitor

- **Success Rate**: Percentage of successful API calls
- **Subdivision Rate**: How often cells are subdivided
- **Error Patterns**: Common error types and frequencies
- **Coverage**: Geographic distribution of discovered locations
- **Performance**: Average response times and throughput

## Troubleshooting

### Common Issues

1. **504 Timeouts**: Check `OVERPASS_TIMEOUT_S` and endpoint rotation
2. **Rate Limiting**: Adjust `DISCOVERY_RATE_LIMIT_QPS` and sleep intervals
3. **Missing Categories**: Verify `categories.yml` has proper `osm_tags`
4. **Database Errors**: Check `DATABASE_URL` and table creation

### Debug Mode

Enable query logging:
```bash
export OSM_LOG_QUERIES=true
```

### Performance Tuning

- **Reduce QPS**: Lower `DISCOVERY_RATE_LIMIT_QPS` for stability
- **Increase Sleep**: Higher `DISCOVERY_SLEEP_BASE_S` for politeness
- **Adjust Timeout**: Increase `OVERPASS_TIMEOUT_S` for slow responses
- **Limit Subdivision**: Lower `MAX_SUBDIVIDE_DEPTH` to reduce API calls

## Compliance Notes

### OSM/Overpass Policy Compliance

- ✅ **User-Agent**: Proper identification header
- ✅ **Rate Limiting**: Respectful request frequency
- ✅ **Read-Only**: No edit API usage
- ✅ **No Scraping**: Only discovery queries
- ✅ **Backoff**: Exponential backoff on errors
- ✅ **Jitter**: Randomized delays to avoid thundering herd

### Best Practices

1. **Monitor Usage**: Regularly check telemetry data
2. **Respect Limits**: Don't exceed recommended QPS
3. **Handle Errors**: Implement proper retry logic
4. **Log Everything**: Use telemetry for debugging
5. **Test Carefully**: Start with small areas and low limits

## Future Enhancements

### Planned Improvements

1. **Caching**: Redis-based query result caching
2. **Smart Subdivision**: ML-based subdivision decisions
3. **Load Balancing**: Intelligent endpoint selection
4. **Real-time Monitoring**: Dashboard for live metrics
5. **Auto-scaling**: Dynamic rate limiting based on success rates

### Contributing

When making changes to the OSM discovery pipeline:

1. **Test Thoroughly**: Use small test areas first
2. **Monitor Compliance**: Ensure OSM policy adherence
3. **Update Documentation**: Keep this guide current
4. **Add Telemetry**: Log new metrics for monitoring
5. **Performance Test**: Verify improvements don't degrade performance

## Support

For issues or questions:
- **Email**: m.kul@lamarka.nl
- **Documentation**: Check this guide and inline code comments
- **Monitoring**: Use the provided SQL queries for analysis
- **Logs**: Check application logs for detailed error information
