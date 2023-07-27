#!/bin/bash
cd /app/api
exec uvicorn main:app --host 0.0.0.0 --port 81