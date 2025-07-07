import os
from dotenv import load_dotenv

class Config:
    # Flask settings
    load_dotenv()
    SECRET_KEY = os.getenv('SECRET_KEY', 'NO_KEY_SET')
    DEBUG = True
    
    # Logging settings
    LOG_LEVEL = 'DEBUG'
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    LOG_FILE = 'app.log'

class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = 'ERROR'