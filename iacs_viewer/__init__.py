from flask import Flask
from iacs_viewer.config import Config, DevelopmentConfig, ProductionConfig
from iacs_viewer.database import db 
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

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

    db.init_app(app)
    # Check DB connection
    with app.app_context():
        try:
            db.session.execute(text('SELECT 1'))
            print("✅ Database connection successful.")
        except OperationalError as e:
            print("❌ Database connection failed:")
            print(e)

    from iacs_viewer.routes.main import main
    app.register_blueprint(main)

    return app