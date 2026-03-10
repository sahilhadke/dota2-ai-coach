import logging
import os

from dotenv import load_dotenv

from dota2_coach.gsi.server import GSIServer
from dota2_coach.gsi.state import build_game_state_dict
from dota2_coach.engine import EventEngine
from dota2_coach.engine.advisor import ItemAdvisor
from dota2_coach.api.app import create_app

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GSI_HOST = "127.0.0.1"
GSI_PORT = 4000
API_PORT = 5050
TOKEN = "TOKENHERE"


def main():
    engine = EventEngine()
    slog = engine.server_log

    api_key = os.getenv("GEMINI_API_KEY", "")
    advisor = None
    if api_key and api_key != "your_key_here":
        advisor = ItemAdvisor(api_key, server_log=slog)
        slog.info("System", "ItemAdvisor enabled (Gemini)")
        logger.info("ItemAdvisor enabled (Gemini)")
    else:
        slog.warn("System", "GEMINI_API_KEY not set — item recommendations disabled")
        logger.warning("GEMINI_API_KEY not set — item recommendations disabled")

    engine._advisor = advisor

    def on_state(game_state):
        if game_state.has_data():
            state_dict = build_game_state_dict(game_state)
            engine.process(state_dict)

    gsi = GSIServer((GSI_HOST, GSI_PORT), TOKEN, on_state=on_state)
    gsi.start()
    slog.info("System", f"GSI server listening on {GSI_HOST}:{GSI_PORT}")

    app = create_app(engine)
    slog.info("System", f"Flask API starting on {GSI_HOST}:{API_PORT}")
    logger.info("Flask API starting on %s:%d", GSI_HOST, API_PORT)
    app.run(host=GSI_HOST, port=API_PORT, use_reloader=False)


if __name__ == "__main__":
    main()
