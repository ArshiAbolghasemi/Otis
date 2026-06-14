"""Entrypoint for running the Otis API with uvicorn."""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("otis.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
