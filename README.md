# A blockchain Dapp for energy management in microgrids

Prerequisites: Docker v20.10, python v3.8.10

Register on https://https://developer.nrel.gov/ and create a file named .apikey in the smart-meter/dataset directory containing the API key received.

Generate the data sets using [the dedicated Jupyter notebook](simulation/load_dataset.ipynb) from the [simulation](simulation/) folder.
For a preconfigured simulation scenario, use [the other Jupyter notebook](simulation/static_simulation.ipynb) from the same folder.

To run the simulation, use the [start-simulation](start-simulation.py) script from the root folder.

Options:
-    -p|--prosumers             Number of prosumers used in simulation (defaults to 2)
-    -h|--help                  Displays help
-    -v|--verbose               Displays verbose output
-    -s|--static                Runs static, preconfigured simulation
-    -t|--timestamp             Simulation start time (UNIX timestamp)
-    -c|--consensus             Consensus algorithm (ethash, clique)
-   -nc|--no-colour             Disables colour output