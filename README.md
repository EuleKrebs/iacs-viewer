# iacs-viewer
This project gives an insight into the IACS dataset published by the Europe-LAND HE Project: https://zenodo.org/records/15692199
## Overview

**iacs-viewer** is a web-based tool designed to help users explore and analyze the IACS (Integrated Administration and Control System) dataset. The application provides interactive visualizations and filtering options to make it easier to gain insights from the data.

## Features

- Interactive data exploration
- Filtering and search capabilities
- Visualizations for key dataset attributes
- User-friendly interface

## Getting Started
1. Clone the repository

    ```bash
    git clone https://github.com/yourusername/iacs-viewer.git
    cd iacs-viewer
    ```

2. Set up a virtual environment and install dependencies

    ```bash
    uv venv
    source .venv/bin/activate
    uv sync
    ```

3. Configure environment variables

    Create a `.env` file in the root directory and add:

    ```env
    FLASK_ENV=development
    SQLALCHEMY_DATABASE_URI=postgresql://your_user:your_password@localhost:5432/DIACS
    SECRET_KEY=your_secret_key
    ```

4. Setup a postgreSQL database

    - Create a database named `DIACS`
    - Ensure the PostGIS extension is enabled:

    ```sql
    CREATE EXTENSION IF NOT EXISTS postgis;
    ```

5. Start the development server

    ```bash
    python run.py
    ```

## Dataset

The IACS dataset is available from [Zenodo](https://zenodo.org/records/15692199). Please download and place the dataset in the appropriate directory as described in the project documentation.

## License

This project is licensed under the MIT License.