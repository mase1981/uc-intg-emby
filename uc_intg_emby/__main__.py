"""Entry point for python -m. :copyright: (c) 2026 by Meir Miyara. :license: MPL-2.0"""
import asyncio

from . import main

if __name__ == "__main__":
    asyncio.run(main())
