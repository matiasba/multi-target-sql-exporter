import yaml
from flask import Flask
from .db import execute_query

with open('app/queries.yaml', 'r') as file:
    queries_config = yaml.safe_load(file)

with open('app/auth.yaml', 'r') as file:
    auth_config = yaml.safe_load(file)


def create_app():
    app = Flask(__name__)

    @app.route('/healthcheck', methods=["GET"])
    def healthcheck():
        return "ok"

    from .scrape import scrape
    app.register_blueprint(scrape)

    return app
