# Default Config
class Config:

    DEBUG = False
    TESTING = False

    DATABASE_URI = "postgresql://admin:admin@localhost/analyzer"
    API_HOST = "0.0.0.0"
    API_PORT = 8080

    ENV_VAR_PREFIX = "ANALYZER_"
