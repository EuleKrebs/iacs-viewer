import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DEBUG = True

    # Optional: PostgreSQL for production data import pipeline
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', '')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Data directory for GeoPackage / GeoParquet files
    DATA_DIR = os.getenv('DATA_DIR', 'data')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
