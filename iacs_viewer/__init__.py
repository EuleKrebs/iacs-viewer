from flask import Flask
from iacs_viewer.config import Config, DevelopmentConfig, ProductionConfig
from iacs_viewer.query_engine import QueryEngine
import os
from dotenv import load_dotenv

# load environment variables
load_dotenv()

env = os.getenv('FLASK_ENV', 'development')
config_class = ProductionConfig if env == 'production' else DevelopmentConfig


def create_app():
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize DuckDB query engine
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    app.config['QUERY_ENGINE'] = QueryEngine(data_dir=data_dir)
    app.config['DATA_DIR'] = data_dir

    # Register blueprints
    from iacs_viewer.routes.main import main
    app.register_blueprint(main)

    from iacs_viewer.routes.api import api
    app.register_blueprint(api, url_prefix='/api')

    from iacs_viewer.routes.populate import bp as populate
    app.register_blueprint(populate, url_prefix='/api/populate')

    return app
