FROM archlinux:latest

RUN pacman -Syu --noconfirm rustup uv python cronie base-devel && pacman -Scc --noconfirm 
RUN rustup default stable

WORKDIR /ibu
COPY . .
RUN ./scripts/setup.sh uv
RUN cargo clean

RUN mkdir -p /var/spool/cron
RUN echo "0 19 * * * cd /ibu && mkdir -p /ibu/logs && /ibu/.venv/bin/python sheepit_scraper.py >> /ibu/logs/cron.log 2>&1" > /var/spool/cron/root
EXPOSE 5000

CMD ["sh", "-c", "crond && ./.venv/bin/uwsgi --http 0.0.0.0:5000 --master --enable-threads --lazy-apps -w IBU_dashboard:app"]