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
