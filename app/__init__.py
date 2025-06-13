import os
from pathlib import Path

from flask import Flask, send_from_directory


def create_app(results_dir: Path) -> Flask:
    # Path to gemtest-webapp's static folder (CSS, JS, etc.)
    # Get the directory of this file (i.e., gemtest_webapp/app/)
    current_dir = Path(__file__).parent
    gemtest_static_path = current_dir / "static"

    # Create Flask app, serving static files from gemtest-webapp
    app = Flask(
        __name__,
        static_folder=str(gemtest_static_path),
        static_url_path="/static"
    )

    # Path to image directory (repo-local, not part of gemtest-webapp)
    image_dir = os.path.join(os.getcwd(), "app", "static", "img")

    # Custom route to serve images
    @app.route("/static/img/<path:filename>")
    def custom_static_img(filename):
        return send_from_directory(image_dir, filename)

    # Add your own app config
    app.config['DIR'] = results_dir

    # Register your blueprint
    from app.routes import bp  # pylint: disable=import-outside-toplevel
    app.register_blueprint(bp)

    return app
