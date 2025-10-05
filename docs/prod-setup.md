# How to setup for production.
>[!IMPORTANT]
> This is not finished yet, and may have incomplete or incorrect steps.

## Requirements
- Rust
- Python

## Instructions
- Clone this repo.
- Run `./scripts/setup.sh` to do inital setup.
- To get the webserver running, run `./scripts/run.sh` This will expose a server on 172.0.0.1:5000.
- Create a `.env` file to configure the app. You can use the provided `.env.example` file as a refrence.
- To scrape team data you can run `sheepit_scraper.py`