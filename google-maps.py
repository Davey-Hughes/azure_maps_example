"""
Google Maps Place Enrichment Tool

This script enriches facility data from an Excel file by fetching additional
information from Google Maps Places API. It uses multithreading to process
multiple facilities concurrently.

Requirements:
    - GOOGLE_MAPS_API_KEY environment variable (loaded from .env file)
    - Input Excel file with columns: OID, facility_url, facility_name

Usage:
    python google-maps.py <input_file> <output_file>
"""

import json
import os
import threading
from queue import Queue
from typing import Annotated
from urllib.parse import urlparse

import googlemaps
import polars as pl
import typer
from dotenv import load_dotenv

# Load environment variables from .env file
_ = load_dotenv()

# Number of concurrent worker threads for API requests
NUM_THREADS = 4


def worker(
    gmaps: googlemaps.Client,
    df: pl.DataFrame,
    inputq: Queue,
    outputq: Queue,
) -> None:
    """
    Worker thread that processes facility queries and fetches Google Maps data.

    Continuously pulls items from the input queue, queries the Google Maps API
    for place information, and pushes enriched results to the output queue.

    Args:
        gmaps: Initialized Google Maps client
        df: Input DataFrame (unused, kept for signature compatibility)
        inputq: Queue containing dicts with 'query_string' and 'oid' keys
        outputq: Queue for storing enriched place data results
    """
    while not inputq.empty():
        try:
            item = inputq.get(block=False)
            print(f"Processing {item['oid']}: {item['query_string']}")

            # Search for the place using text query
            place = gmaps.find_place(item["query_string"], input_type="textquery")

            # If a candidate is found, fetch detailed information
            if place["candidates"]:
                place_details = gmaps.place(
                    place["candidates"][0]["place_id"],
                    fields=[
                        "name",
                        "formatted_address",
                        "formatted_phone_number",
                        "opening_hours",
                        "url",
                        "editorial_summary",
                    ],
                )["result"]

                # Extract and structure the place details
                outputq.put(
                    {
                        "OID": item["oid"],
                        "name": place_details.get("name"),
                        "address": place_details.get("formatted_address"),
                        "phone": place_details.get("formatted_phone_number"),
                        "url": place_details.get("url"),
                        "summary": place_details.get("editorial_summary", {}).get(
                            "overview"
                        ),
                        "hours": json.dumps(place_details.get("opening_hours")),
                    }
                )
        finally:
            # Mark task as done even if an exception occurred
            inputq.task_done()


def main(
    input_file: str, output_file: str, num_rows: Annotated[int, typer.Argument()] = -1
) -> None:
    """
    Main function to enrich facility data with Google Maps information.

    Reads an Excel file containing facility data, queries Google Maps API
    for additional information using multithreading, and writes the enriched
    data to an output Excel file.

    Args:
        input_file: Path to input Excel file with facility data
        output_file: Path to output Excel file for enriched data

    Raises:
        KeyError: If GOOGLE_MAPS_API_KEY environment variable is not set
    """
    # Initialize Google Maps client with API key
    gmaps = googlemaps.Client(key=os.environ["GOOGLE_MAPS_API_KEY"])

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

        # Use domain name if available, otherwise use facility name
        query = url.hostname if url.hostname else name

        inputq.put({"query_string": query, "oid": oid})

    # Create and start worker threads
    threads = []
    for i in range(NUM_THREADS):
        thread = threading.Thread(target=worker, args=(gmaps, df, inputq, outputq))
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
