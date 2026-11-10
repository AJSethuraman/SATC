import logging

from dotenv import load_dotenv

from .blizzard import BlizzardClient
from .bot import GuildBot
from .config import load
from .db import Database


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()
    cfg = load()
    db = Database(cfg.db_path)
    blizzard = BlizzardClient(cfg.blizzard_client_id, cfg.blizzard_client_secret, cfg.region)
    GuildBot(cfg, db, blizzard).run(cfg.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
