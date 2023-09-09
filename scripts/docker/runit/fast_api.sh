#!/bin/sh -i
cd /app/api
uvicorn main:app --host 0.0.0.0 --port 81