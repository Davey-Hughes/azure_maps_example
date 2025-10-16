"""
Google Maps Place Enrichment Tool

This script enriches facility data from an Excel file by fetching additional
information from Google Maps Places API. It uses multithreading to process
multiple facilities concurrently.

The script queries Google Maps using facility URLs (hostname) and/or facility
names, retrieving details such as address, phone number, website, opening hours,
and AI-generated summaries. Results are merged with the original data and
exported to Excel.

Requirements:
    - GOOGLE_MAPS_API_KEY environment variable (loaded from .env file)
    - Input Excel file with columns: OID, facility_url, facility_name
    - Python packages: polars, typer, requests, python-dotenv

Usage:
    python google-maps.py <input_file> <output_file> [num_rows] [--rate-limit RATE]

    Arguments:
        input_file: Path to input Excel file with facility data
        output_file: Path to output Excel file for enriched data
        num_rows: Optional number of rows to process (default: -1 for all rows)

    Options:
        --rate-limit: Maximum API requests per minute (default: 60, 0 for unlimited)

    Examples:
        python google-maps.py facilities.xlsx enriched_facilities.xlsx
        python google-maps.py facilities.xlsx enriched_facilities.xlsx 50
        python google-maps.py facilities.xlsx enriched_facilities.xlsx --rate-limit 30
        python google-maps.py facilities.xlsx enriched_facilities.xlsx 100 --rate-limit 45
"""

from collections import deque
import json
import os
import threading
import time
from queue import Queue
from typing import Annotated, TypedDict
from urllib.parse import urlparse
import requests

import polars as pl
import typer
from dotenv import load_dotenv

# Load environment variables from .env file
_ = load_dotenv()

# Number of concurrent worker threads for API requests
NUM_THREADS = 4


class RateLimiter:
    """Thread-safe rate limiter for API requests.

    Controls the rate of requests by enforcing a minimum time interval
    between consecutive requests across multiple threads.

    Attributes:
        requests_per_minute: Maximum number of requests allowed per minute
        min_interval: Minimum time interval between requests in seconds
        last_request_time: Timestamp of the last request
        lock: Threading lock for thread-safe operation
    """

    def __init__(self, requests_per_minute: int):
        """Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum number of requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute if requests_per_minute > 0 else 0
        self.last_request_time = 0.0
        self.lock = threading.Lock()

    def wait(self):
        """Block until enough time has passed to make the next request.

        Ensures that requests are spaced out according to the configured rate limit.
        This method is thread-safe and can be called from multiple worker threads.
        """
        with self.lock:
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time

            if time_since_last_request < self.min_interval:
                sleep_time = self.min_interval - time_since_last_request
                time.sleep(sleep_time)

            self.last_request_time = time.time()


class Coords(TypedDict):
    """Type definition for geographic coordinates.

    Attributes:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
    """

    lat: float
    lon: float


class GoogleMaps:
    """Client for interacting with Google Maps Places API.

    Attributes:
        api_key: Google Maps API key for authentication
    """

    api_key: str

    def __init__(self, api_key: str):
        """Initialize the Google Maps client.

        Args:
            api_key: Google Maps API key
        """
        self.api_key = api_key

    def text_search(
        self,
        query: str,
        coords: Coords | None = None,
        max_results: int = 1,
        field_mask: list[str] = ["places.id"],
    ):
        """Search for places using a text query.

        Performs a text-based search for places, optionally biased toward a
        geographic location. The query is automatically scoped to Colorado Springs.

        Args:
            query: Text search query (e.g., business name or URL hostname)
            coords: Optional geographic coordinates to bias search results
            max_results: Maximum number of results to return (default: 1)
            field_mask: List of place fields to retrieve (default: ["places.id"])

        Returns:
            dict: JSON response from Google Maps Places API containing place data
        """
        location_bias = (
            {
                "circle": {
                    "center": {
                        "latitude": coords["lat"],
                        "longitude": coords["lon"],
                    },
                    "radius": 50000.0,
                }
            }
            if coords
            else None
        )

        return requests.post(
            "https://places.googleapis.com/v1/places:searchText",
            json={
                "textQuery": f"{query} in Colorado Springs",
                "maxResultCount": max_results,
                "locationBias": location_bias,
            },
            headers={
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": ",".join(field_mask),
            },
        ).json()

    def place_details(self, id: str, field_mask: list[str]):
        """Fetch detailed information for a specific place by ID.

        Note: This method is not currently used since text_search can retrieve
        all needed details directly with an appropriate field mask.

        Args:
            id: Google Maps place ID
            field_mask: List of place fields to retrieve

        Returns:
            dict: JSON response containing place details
        """
        return requests.get(
            f"https://places.googleapis.com/v1/places/{id}",
            headers={
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": ",".join(field_mask),
            },
        ).json()


def worker(
    gmaps: GoogleMaps,
    df: pl.DataFrame,
    inputq: Queue,
    outputq: Queue,
    rate_limiter: RateLimiter | None = None,
) -> None:
    """Worker thread that processes facility queries and fetches Google Maps data.

    Continuously pulls items from the input queue, queries the Google Maps API
    for place information, and pushes enriched results to the output queue.

    The worker implements a fallback mechanism: if the initial query (typically
    the URL hostname) returns no results and a facility name is available, it
    will retry with the facility name.

    Args:
        gmaps: Initialized Google Maps client
        df: Input DataFrame (unused, kept for signature compatibility)
        inputq: Queue containing dicts with 'query_list' (deque of query strings)
            and 'oid' (facility ID) keys
        outputq: Queue for storing enriched place data results as dictionaries
        rate_limiter: Optional rate limiter to control API request frequency

    Note:
        Each item from inputq contains a deque of queries to try in order,
        allowing fallback from URL hostname to facility name if needed.
    """
    while not inputq.empty():
        try:
            item = inputq.get(block=False)
            query = item["query_list"].popleft()
            print(f"Processing {item['oid']}: {query}")

            # Wait for rate limiter before making API request
            if rate_limiter:
                rate_limiter.wait()

            # Search for the place using text query
            place_results = gmaps.text_search(
                query,
                # {"lat": 38.8407721, "lon": -104.8244929},
                field_mask=[
                    "places.id",
                    "places.displayName",
                    "places.formattedAddress",
                    "places.regularOpeningHours",
                    "places.nationalPhoneNumber",
                    "places.websiteUri",
                    "places.googleMapsUri",
                    "places.editorialSummary",
                    "places.generativeSummary",
                ],
            )

            # If a candidate is found, fetch detailed information
            if place_results and "places" in place_results:
                place_details = place_results["places"][0]

                # Extract and structure the place details
                outputq.put(
                    {
                        "OID": item["oid"],
                        "name": place_details.get("displayName")["text"],
                        "address": place_details.get("formattedAddress"),
                        "phone": place_details.get("nationalPhoneNumber"),
                        "url": place_details.get("websiteUri"),
                        "googleMapsUri": place_details.get("googleMapsUri"),
                        "summary": place_details.get("editorialSummary", {})
                        .get("generativeSummary", {})
                        .get("overview"),
                        "hours": json.dumps(place_details.get("regularOpeningHours")),
                    }
                )

            else:
                print(f"No results found for {query}")
                if item["query_list"]:
                    inputq.put(item)
        finally:
            # Mark task as done even if an exception occurred
            inputq.task_done()


def main(
    input_file: str,
    output_file: str,
    num_rows: Annotated[int, typer.Argument()] = -1,
    rate_limit: Annotated[
        int, typer.Option(help="Maximum requests per minute (0 for unlimited)")
    ] = 500,
) -> None:
    """Main function to enrich facility data with Google Maps information.

    Reads an Excel file containing facility data, queries Google Maps API
    for additional information using multithreading, and writes the enriched
    data to an output Excel file.

    The enrichment process:
    1. Reads input Excel file with facility data
    2. Creates work queue with facility queries (URL hostname and/or name)
    3. Spawns worker threads to process queries concurrently
    4. Collects enriched data including address, phone, hours, and summaries
    5. Merges enriched data with original data and exports to Excel

    Args:
        input_file: Path to input Excel file with facility data
            Expected columns: OID, facility_url, facility_name
        output_file: Path to output Excel file for enriched data
        num_rows: Number of rows to process from input file (default: -1 for all)
        rate_limit: Maximum number of API requests per minute (default: 60, 0 for unlimited)

    Raises:
        KeyError: If GOOGLE_MAPS_API_KEY environment variable is not set

    Example:
        main("facilities.xlsx", "enriched.xlsx", num_rows=100)
    """
    # Initialize Google Maps client with API key
    gmaps = GoogleMaps(os.environ["GOOGLE_MAPS_API_KEY"])

    # Initialize rate limiter
    rate_limiter = RateLimiter(rate_limit) if rate_limit > 0 else None
    if rate_limiter:
        print(f"Rate limit: {rate_limit} requests per minute")

    # Read input Excel file
    df = pl.read_excel(input_file)

    # Create empty DataFrame for enriched data with predefined schema
    enriched_data = pl.DataFrame(
        schema={
            "OID": str,
            "name": str,
            "address": str,
            "phone": str,
            "url": str,
            "googleMapsUri": str,
            "summary": str,
            "hours": str,
        }
    )

    # Create queues for coordinating work between threads
    inputq = Queue()
    outputq = Queue()

    # Populate input queue with facility queries
    # Note: Currently limited to first 20 rows for testing
    for row in df.head(num_rows).iter_rows(named=True):
        oid = row["OID"]
        url = urlparse(row["facility_url"])
        name = row["facility_name"]

        queries = deque([])
        if url.hostname:
            queries.append(url.hostname)

        if name:
            queries.append(name)

        inputq.put({"query_list": queries, "oid": oid})

    # Create and start worker threads
    threads = []
    for i in range(NUM_THREADS):
        thread = threading.Thread(
            target=worker, args=(gmaps, df, inputq, outputq, rate_limiter)
        )
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Collect results from output queue and build enriched DataFrame
    while not outputq.empty():
        enriched_data.extend(pl.DataFrame(outputq.get(block=False)))

    # Merge original data with enriched data and write to output file
    result_df = pl.concat([df, enriched_data], how="align")
    result_df.write_excel(output_file)


if __name__ == "__main__":
    typer.run(main)
