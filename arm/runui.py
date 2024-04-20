"""
Automatic Ripping Machine - User Interface (UI)
Provided for free and hosted on GitHub under the MIT License
https://github.com/automatic-ripping-machine/automatic-ripping-machine
"""
from waitress import serve

from ui_config import UIConfig
from ui import create_app

if __name__ == '__main__':
    ui_config = UIConfig()
    app = create_app()
    app.logger.info(f"Starting ARM UI on interface address - {ui_config.server_host}:{ui_config.server_port}")
    serve(app, host=ui_config.server_host, port=ui_config.server_port)
