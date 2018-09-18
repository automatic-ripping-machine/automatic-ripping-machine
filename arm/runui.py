from ui import app
from config.config import cfg

if __name__ == '__main__':
    app.run(host=cfg['WEBSERVER_IP'], port=cfg['WEBSERVER_PORT'], debug=True)
    # app.run(debug=True)
