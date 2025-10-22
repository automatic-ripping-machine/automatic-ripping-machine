"""
Automatic Ripping Machine - User Interface (UI)
Provided for free and hosted on GitHub under the MIT License
https://github.com/automatic-ripping-machine/automatic-ripping-machine
"""
from waitress import serve
from ui import create_app

if __name__ == '__main__':
    app = create_app()

    # Check if debug mode is enabled (via config or environment)
    flask_debug = app.config.get("FLASK_DEBUG") or os.environ.get("FLASK_DEBUG")

    if flask_debug and str(flask_debug).lower() in ("1", "true", "yes", "on"):
        # Run Flask’s built-in debug server
        app.run(
            host=app.config.get("SERVER_HOST", "127.0.0.1"),
            port=app.config.get("SERVER_PORT", 5000),
            debug=True
        )
    else:
        # Run Waitress for production
        serve(
            app,
            host=app.config.get("SERVER_HOST", "0.0.0.0"),
            port=app.config.get("SERVER_PORT", 5000),
            threads=40
        )
