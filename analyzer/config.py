MEGABYTE = 1024 * 1024


# Default Config
class Config:
    """
    Default values for the app to start.

    Parser from module analyzer.utils.arg_parse.get_arg_parser()
    uses these values as default
    """

    # app configuration variables
    DEBUG = False
    TESTING = False

    # API variables
    API_HOST = "0.0.0.0"
    API_PORT = 8080
    MAX_REQUEST_SIZE = 64 * MEGABYTE

    # Database variables
    DATABASE_URI = "postgresql://admin:admin@localhost/analyzer"
    DATABASE_MAX_QUERY_ARGS = 32767
    DATABASE_PG_POOL_MIN_SIZE = 10
    DATABASE_PG_POOL_MAX_SIZE = 10

    # env parser variables
    ENV_VAR_PREFIX = "ANALYZER_"

    # Logging variables
    LOG_LEVEL = "info"
    LOG_FORMAT = "color"

    # format variables
    BIRTH_DATE_FORMAT = "%d.%m.%Y"
