import os
import sys

from aiohttp import web
from setproctitle import setproctitle

from analyzer.api.app import init_app
from analyzer.config import DebugConfig
from analyzer.utils.argparse import get_arg_parser
from analyzer.utils.logging import set_logging


def run_dev():
    import subprocess

    subprocess.run(["adev", "runserver", "analyzer/api/debug.py"])


app = None
parser = None
cfg = DebugConfig()

parser = get_arg_parser(cfg)
args = parser.parse_args()

set_logging(args.log_level, args.log_format)

setproctitle(f"[Dev] {os.path.basename(sys.argv[0])}")

app = init_app(args, cfg)

if __name__ == "__main__":
    web.run_app(app)
