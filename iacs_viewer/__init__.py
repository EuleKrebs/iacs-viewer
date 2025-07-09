from flask import Flask
from iacs_viewer.config import Config, DevelopmentConfig, ProductionConfig
import os
from dotenv import load_dotenv

# load  environment variables
load_dotenv()
# Selects the environment based on the FLASK_ENV environment variable
# Defaults to development if not set
env = os.getenv('FLASK_ENV', 'development')
# select the configuration class based on the environment
config_class = ProductionConfig if env == 'production' else DevelopmentConfig

def create_app():
    app = Flask(__name__)
    app.config.from_object(config_class)

    from iacs_viewer.routes.main import main
    app.register_blueprint(main)

    return app