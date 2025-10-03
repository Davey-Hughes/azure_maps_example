# Azure Maps Search Client

A Python client for searching points of interest (POI) and geocoding addresses using Azure Maps API.

## Features

- **Geocoding**: Convert addresses to geographic coordinates
- **POI Search**: Search for businesses and points of interest with optional filters
- **Opening Hours**: Retrieve opening hours information for the next seven days

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

1. Install uv (if not already installed)
2. Sync dependencies from `pyproject.toml`:
   ```bash
   uv sync
   ```
3. Activate the virtual environment:
   ```bash
   source ./venv/bin/activate
   ```

## Configuration

1. Copy the environment template:
   ```bash
   cp env_template .env
   ```

2. Add your Azure Maps subscription key to `.env`:
   ```
   SUBSCRIPTION_KEY=your_azure_maps_key_here
   ```

### Getting Azure Maps Credentials

- [Subscription Key Setup Guide](https://learn.microsoft.com/en-us/azure/azure-maps/how-to-dev-guide-py-sdk#using-a-subscription-key-credential)
- [Azure Maps Account Creation](https://learn.microsoft.com/en-us/azure/azure-maps/quick-demo-map-app#create-an-azure-maps-account)

## Usage

Run the example script:
```bash
python main.py
```

### API Reference

See the [POI Search API documentation](https://learn.microsoft.com/en-us/rest/api/maps/search/get-search-poi?view=rest-maps-1.0&tabs=HTTP) for available request parameters and response data.

## Important Notes

- **Location Filtering**: For accurate results, provide both `countrySet` and `coords` parameters. Without these, you may receive results from anywhere in the world.
- **Best Practices**: Use the `geocode()` method first to get precise coordinates for your search area, which typically yields better POI search results.
