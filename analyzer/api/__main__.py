import logging
import os
import sys

from aiohttp import web
from aiomisc import bind_socket
from setproctitle import setproctitle

from analyzer.api.app import init_app
from analyzer.config import Config
from analyzer.utils.argparse import get_arg_parser
from analyzer.utils.logging import set_logging

app = None
parser = None
cfg = Config()


def run_app() -> None:
    parser = get_arg_parser(cfg)
    args = parser.parse_args()

    set_logging(args.log_level, args.log_format)

    # allocate socket on behalf of super user
    sock = bind_socket(address=args.api_host, port=args.api_port, proto_name="http")
    setproctitle(os.path.basename(sys.argv[0]))

    """
    # To add more workers, use snippet:
    # Do `pip install forklib`
    # Add forklib to requirements.txt
    import forklib
    
    def worker():
        setproctitle(f"[Worker] {os.path.basename(sys.argv[0])}")
        app = init_app(args)
        web.run_app(app, sock=sock)
        
    forklib.fork(os.cpu_count(), worker, auto_restart=True)
    """

    app = init_app(args, cfg)
    web.run_app(app, sock=sock)

    # Set current process owner to user provided by argparser
    # It is suggested for current user to be low-privelleged for safety reasons
    if args.user is not None:
        logging.info(f"Changing user to {args.user.pw_name}")
        os.setgid(args.user.pw_gid)
        os.setuid(args.user.pw_uid)


if __name__ == "__main__":
    run_app()
