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

2. Add your API keys to `.env`:
   ```
   SUBSCRIPTION_KEY=your_azure_maps_key_here
   GOOGLE_MAPS_API_KEY=your_google_maps_key_here
   ```

### Getting API Credentials

**Azure Maps:**
- [Subscription Key Setup Guide](https://learn.microsoft.com/en-us/azure/azure-maps/how-to-dev-guide-py-sdk#using-a-subscription-key-credential)
- [Azure Maps Account Creation](https://learn.microsoft.com/en-us/azure/azure-maps/quick-demo-map-app#create-an-azure-maps-account)

**Google Maps:**
- [Get API Key](https://developers.google.com/maps/documentation/javascript/get-api-key)
- [Places API Documentation](https://developers.google.com/maps/documentation/places/web-service/overview)

## Usage

### Azure Maps Search (azure-maps.py)

Run the example script:
```bash
python azure-maps.py
```

#### API Reference

See the [POI Search API documentation](https://learn.microsoft.com/en-us/rest/api/maps/search/get-search-poi?view=rest-maps-1.0&tabs=HTTP) for available request parameters and response data.

### Google Maps Place Enrichment (google-maps.py)

Enrich facility data from an Excel file with Google Maps Places API information. The script uses multithreading for efficient concurrent processing.

#### Basic Usage

```bash
python google-maps.py <input_file> <output_file>
```

**Example:**
```bash
python google-maps.py facilities.xlsx enriched_facilities.xlsx
```

#### Limit Number of Rows (Optional)

Process only a specific number of rows from the input file:
```bash
python google-maps.py facilities.xlsx output.xlsx --num-rows 50
```

To process all rows, omit the `--num-rows` parameter or use `-1`.

#### Input File Requirements

Your Excel file must contain these columns:
- `OID` - Unique identifier for each facility
- `facility_url` - URL of the facility (domain will be extracted for search)
- `facility_name` - Name of the facility (used as fallback if URL is missing)

#### Output Data

The script adds the following columns to your data:
- `name` - Official name from Google Maps
- `address` - Formatted address
- `phone` - Formatted phone number
- `url` - Google Maps URL for the place
- `hours` - Opening hours (JSON format)
- `summary` - Editorial summary/description

#### Performance

The script uses 4 concurrent threads by default. You can adjust this by modifying the `NUM_THREADS` constant in `google-maps.py`.

## Important Notes

- **Location Filtering**: For accurate results, provide both `countrySet` and `coords` parameters. Without these, you may receive results from anywhere in the world.
- **Best Practices**: Use the `geocode()` method first to get precise coordinates for your search area, which typically yields better POI search results.



