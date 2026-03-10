#!/bin/bash
lsof -ti :4000 | xargs kill -9 2>/dev/null; echo "Port 4000 freed"
lsof -ti :5050 | xargs kill -9 2>/dev/null; echo "Port 5050 freed"