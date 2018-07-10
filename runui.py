#!/usr/bin/python3

# import sys
# from .arm import config
from armui import app

if __name__ == '__main__':
    app.run(host='10.10.10.174', port='8080', debug=True)
    # app.run(debug=True)

# if __name__ == "__main__":
#     from sys import argv

    # if len(argv) == 2:
    #     logserve.run(port=int(argv[1]))
    # else:
    #     logserve.run()