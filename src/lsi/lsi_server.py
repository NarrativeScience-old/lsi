"""Rest interface to LSI."""
import argparse
import sys

from flask import Flask, jsonify, request

from utils.hosts import get_entries

class LsiServer(object):
    """LSI server, serving JSON information for hosts."""
    def __init__(self, host, port):
        """Initializer."""
        self._host = host
        self._port = port

    def run_server(self):
        """Start the server."""
        app = self._make_app()
        app.run(host=self._host, port=self._port)

    def _make_app(self):
        """Create a flask app and set up routes on it.

        :return: A flask app.
        :rtype: :py:class:`Flask`
        """
        app = Flask(__name__)

        @app.route("/list-instances")
        def list_instances():
            """Return a JSON list of all instance information."""
            latest_arg = request.args.get('latest', "False")
            # The querystring comes in as a string; convert it to a bool here.
            latest = latest_arg.lower().strip() == "true"
            entries = get_entries(latest=latest)
            return jsonify(entries=[e.to_dict() for e in entries])

        @app.route("/health-check")
        def health_check():
            """Return the string "ok" for a health check."""
            return "ok"
                                       
        return app

def get_args():
    """Get command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0", help="Host to listen on.")
    parser.add_argument("--port", default=5678, help="Port to listen on.")
    return parser.parse_args()

def main():
    """Main entry point."""
    args = get_args()
    server = LsiServer(host=args.host, port=args.port)
    server.run_server()
