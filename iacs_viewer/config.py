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
    LOG_FILE = 'logs/app.log'

    # db settings
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = 'ERROR'

class CoolConfig(object):
    SQLALCHEMY_DATABASE_URI = "postgresql://cnoll:1234@localhost:5432/cool_db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False