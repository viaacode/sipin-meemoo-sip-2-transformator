# sipin-meemoo-sip-2-transformator

## Synopsis

A service that transforms a meemoo SIP to a (python) model.

## Usage

Included in this repository is a config.yml file detailing the required configuration. There is also an .env.example file containing all the needed env variables used in the config.yml file. All values in the config have to be set in order for the application to function correctly. You can use !ENV ${EXAMPLE} as a config value to make the application get the EXAMPLE environment variable.

Install the package and its dependencies. Access to the meemoo PyPi registry is required.

```sh
pip install ".[dev]" \
    --extra-index-url http://do-prd-mvn-01.do.viaa.be:8081/repository/pypi-all/simple \
    --trusted-host do-prd-mvn-01.do.viaa.be
```

Start the service.

```sh
python main.py
```

## Release

SSH into the sipin VM and set the required environment variables.
Create a tag `vX.Y.Z` to deploy a new release to production.
