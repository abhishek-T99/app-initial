# Configuration

Configuration variables are stored in `core/config.py` file. This makes the configuration variables available throughout the application. These variables can be set from `.env` file. If the variable is not found in `.env` file, it will be set to the default value if provided, else, it raises an exception during the application startup.

## Priority for fetching configuration variable values

*   Defined in .env file
*   Defined in Config class of `core/config.py`
*   Exception

Please refer to the [Settings Management](https://docs.pydantic.dev/latest/usage/settings/) section of the Pydantic documentation for more details.

Please see `core/config.py` for all the available configuration variables.

Or talk to your team lead to get the `.env` file for different environments.
