# Default Config
class Config:
    """
    Default values for the app to start.

    Parser from module analyzer.utils.arg_parse.get_arg_parser()
    uses these values as default
    """

    DEBUG = False
    TESTING = False

    DATABASE_URI = "postgresql://admin:admin@localhost/analyzer"
    API_HOST = "0.0.0.0"
    API_PORT = 8080

    ENV_VAR_PREFIX = "ANALYZER_"
