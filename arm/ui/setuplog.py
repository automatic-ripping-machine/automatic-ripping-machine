from logging.config import dictConfig

def setuplog(config):
    # Setup logging, but because of werkzeug issues, we need to set up that later down file
    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s ARM: %(module)s.%(funcName)s %(message)s',
        }},
        'handlers': {
            'wsgi': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://flask.logging.wsgi_errors_stream',
                'formatter': 'default'
            },
            "console": {"class": "logging.StreamHandler", "level": "INFO"},
            "null": {"class": "logging.NullHandler"},
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['wsgi']
        },
    })

    return dictConfig