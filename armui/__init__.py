from flask import Flask


app = Flask(__name__)

import armui.routes  # noqa: E402
import armui.config  # noqa: E402
import armui.utils  # noqa: E402,F401