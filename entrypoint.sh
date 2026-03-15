#!/bin/bash

waitress-serve --port 5000 --call 'iacs_viewer:create_app'
