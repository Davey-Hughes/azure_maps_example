import os
from typing import Any, List, TypedDict
import requests
from pprint import pprint

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.maps.search import MapsSearchClient


from dotenv import load_dotenv

_ = load_dotenv()


class Coords(TypedDict):
    """Type definition for geographic coordinates.

    Attributes:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
    """

    lat: float
    lon: float


class AzureMaps:
    """Client for interacting with Azure Maps search services.

    Provides methods for geocoding addresses and searching for points of interest (POI).
    """

    def _getSearchClient(self):
        """Initialize the Azure Maps search client with API credentials."""
        self.search_client: MapsSearchClient = MapsSearchClient(
            credential=AzureKeyCredential(os.environ["SUBSCRIPTION_KEY"])
        )

    def __init__(self):
        self._getSearchClient()

    def geocode(self, query: str) -> Coords | None:
        """Convert an address or place name to geographic coordinates.

        Args:
            query: Address or place name to geocode

        Prints the longitude and latitude of the first result, or "No results" if none found.
        """
        try:
            result = self.search_client.get_geocoding(query=query)
            if result.get("features", False):
                coordinates = result["features"][0]["geometry"]["coordinates"]
                longitude = coordinates[0]
                latitude = coordinates[1]

                return {"lat": latitude, "lon": longitude}
            else:
                print("No results")

        except HttpResponseError as exception:
            if exception.error is not None:
                print(f"Error Code: {exception.error.code}")
                print(f"Message: {exception.error.message}")

    def poi(
        self,
        query: str,
        coords: Coords | None = None,
        countrySet: list[str] | None = None,
    ) -> List[Any]:
        """Search for points of interest matching a query.

        Args:
            query: Search query for the point of interest (e.g., business name)
            coords: Optional coordinates to center the search around
            countrySet: Optional list of country codes to limit search (e.g., ["US"])

        Returns:
            List of POI results containing location and business information

        Prints information for each result including name, URL, phone, address, and opening hours.
        """
        response = requests.get(
            "https://atlas.microsoft.com/search/poi/json",
            params={
                "api-version": "1.0",
                "query": query,
                "openingHours": "nextSevenDays",
                "countrySet": countrySet,
                "lat": coords["lat"] if coords else None,
                "lon": coords["lon"] if coords else None,
            },
            headers={"subscription-key": os.environ["SUBSCRIPTION_KEY"]},
        ).json()

        res = []

        for result in response["results"]:
            if "poi" in result:
                res.append(result)
                poi = result["poi"]

                if "name" in poi:
                    print(result["poi"]["name"])

                if "url" in poi:
                    print(poi["url"])

                if "phone" in poi:
                    print(poi["phone"])

                if "address" in poi:
                    if "freeformAddress" in poi["address"]:
                        print(poi["address"]["freeformaddress"])

                if "openingHours" in poi:
                    pprint(result["poi"]["openingHours"])
                else:
                    print("No opening hours information")

            print()

        return res


def main():
    """Example usage of the Maps client to search for a specific business."""
    maps = AzureMaps()
    query = "Vans, Seattle"
    coords = AzureMaps().geocode("Vans, Seattle")
    maps.poi(query, coords)


if __name__ == "__main__":
    main()
