import sys
sys.path.append("D:\\arm\\automatic-ripping-machine")

from arm.ui import app  # noqa E402
from arm.config.config import cfg  # noqa E402
import arm.ui.routes  # noqa E402

if __name__ == '__main__':
    app.run(host=cfg['WEBSERVER_IP'], port=cfg['WEBSERVER_PORT'], debug=True)
    # app.run(debug=True)
