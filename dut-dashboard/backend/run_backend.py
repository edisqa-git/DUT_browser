from __future__ import annotations

from app.main import app


def main() -> None:
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="DUT Browser backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
