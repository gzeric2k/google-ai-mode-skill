"""
Wrapper to run search.py with UTF-8 stdout
"""

import sys, os

sys.stdout.reconfigure(encoding="utf-8")

# Now run the search
from search import main

sys.argv = [
    "search.py",
    "--query",
    "粤海投资 00270 主营业务 东深供水 投资要点 业务分析 2025",
    "--save",
    "--debug",
]
main()
