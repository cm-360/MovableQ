import argparse
import asyncio

from hypercorn.asyncio import serve
from hypercorn.config import Config

from app import create_app


def try_load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass

if __name__ == "__main__":
    try_load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true", help="Run in development mode")
    args = parser.parse_args()

    host = "0.0.0.0"
    port = 8080

    app = create_app()

    if args.dev:
        app.run(host=host, port=port, debug=True)
    else:
        # Serve with Hypercorn ASGI server
        config = Config()
        config.bind = [f"{host}:{port}"]
        asyncio.run(serve(app, config))
