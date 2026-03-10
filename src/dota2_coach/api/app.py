import os
from flask import Flask, jsonify, request, send_from_directory
from dota2_coach.engine import EventEngine

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def create_app(engine: EventEngine) -> Flask:
    app = Flask(__name__)

    @app.route("/", methods=["GET"])
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.route("/state", methods=["GET"])
    def get_state():
        return jsonify(engine.current_state)

    @app.route("/events", methods=["GET"])
    def get_events():
        event_type = request.args.get("type")
        return jsonify(engine.bus.get_events(event_type=event_type))

    @app.route("/recommendation", methods=["GET"])
    def get_recommendation():
        if engine.advisor is None:
            return jsonify({"error": "ItemAdvisor not configured"}), 503
        rec = engine.advisor.latest_recommendation
        return jsonify(rec or {})

    @app.route("/full-recommendation", methods=["POST"])
    def trigger_full_recommendation():
        if engine.advisor is None:
            return jsonify({"error": "ItemAdvisor not configured"}), 503
        state = engine.current_state
        if not state:
            return jsonify({"error": "No game state available"}), 400
        engine.advisor.full_recommend(state, player_context=engine.player_context)
        return jsonify({"status": "requesting"})

    @app.route("/full-recommendation", methods=["GET"])
    def get_full_recommendation():
        if engine.advisor is None:
            return jsonify({"error": "ItemAdvisor not configured"}), 503
        rec = engine.advisor.latest_full_build
        return jsonify(rec or {})

    @app.route("/logs", methods=["GET"])
    def get_logs():
        since = request.args.get("since", 0, type=float)
        return jsonify(engine.server_log.get_entries(since=since))

    @app.route("/player-context", methods=["GET"])
    def get_player_context():
        ctx = engine.player_context
        return jsonify(ctx or {})

    @app.route("/player-context", methods=["POST"])
    def set_player_context():
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "invalid JSON"}), 400
        engine.player_context = {
            "lane": data.get("lane", ""),
            "position": data.get("position", ""),
            "lane_ally": data.get("lane_ally", ""),
            "lane_enemies": data.get("lane_enemies", []),
        }
        return jsonify({"status": "ok"})

    return app
