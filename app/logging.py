import logging

from app.config import Settings


def setup_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s : %(message)s",
    )
    logging.getLogger("httpx").setLevel(
        logging.WARNING
    )  # httpx logs URLs at INFO, and the NASA API key was in the query string.
