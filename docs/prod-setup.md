# Local Production Setup

> [!IMPORTANT]
> This is not finished yet, and may have incomplete or incorrect steps.

## Requirements

- Rust
- Python

## Instructions

- Clone this repo.
- Run `./scripts/setup.sh` to do initial setup.
- To get the webserver running, run `./scripts/run.sh` This will expose a server on 172.0.0.1:5000.
- Create a `.env` file to configure the app. You can use the provided `.env.example` file as a reference.
- To scrape team data you can run `sheepit_scraper.py`

# Docker Production Setup.

## Requirements

- Docker

## Instructions

- Clone this repo.
- Edit `docker-compose.yml.example` and save it as `docker-compose.yml`
- Run `docker compose up -d --build`
