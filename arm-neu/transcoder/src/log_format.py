"""
Shared structlog formatters for ARM Transcoder.

Extracted from main.py so transcoder.py can import formatters
without a circular dependency (main → transcoder → main).
"""

import structlog

_foreign_pre_chain = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
]


def json_formatter():
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_foreign_pre_chain,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )


def console_formatter():
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_foreign_pre_chain,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=True),
        ],
    )
