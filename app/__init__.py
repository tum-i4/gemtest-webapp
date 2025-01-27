from pathlib import Path

from flask import Flask


def create_app(results_dir: Path) -> Flask:
    app = Flask(__name__)

    app.config['DIR'] = results_dir
    from app.routes import bp  # pylint: disable=import-outside-toplevel
    app.register_blueprint(bp)

    return app
