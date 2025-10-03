### Installation
I used [uv](https://docs.astral.sh/uv/).
If you install uv, it is as simple as running `uv sync` to sync the installed
packages from the `pyproject.toml` file.

Then source the virtual environment using a command such as `source
./venv/bin/activate`

### Usage
Make sure to follow the installation steps.

Copy the `env_template` file to a file called `.env` and add your Azure Maps
key [like in this
documentation](https://learn.microsoft.com/en-us/azure/azure-maps/how-to-dev-guide-py-sdk#using-a-subscription-key-credential).

For more information about setting up Azure Maps, you can follow the [Azure
Maps
demo](https://learn.microsoft.com/en-us/azure/azure-maps/quick-demo-map-app#create-an-azure-maps-account).

Run `python main.py`

### Notes
(The documentation here)[https://learn.microsoft.com/en-us/rest/api/maps/search/get-search-poi?view=rest-maps-1.0&tabs=HTTP] shows which data can be sent and returned for the POI request.

It is important to send the country and {lat, lon} (I'm not sure if country is
really needed if {lat, lon} are specified). Otherwise you will get random
results from around the entire world. I am not sure if using this geocode
function to get the {lat, lon} is better, but it seems to give better results.
