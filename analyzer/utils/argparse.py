import os
import pwd

from argparse import ArgumentTypeError
from aiomisc.log import LogFormat
from configargparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from typing import Callable
from yarl import URL

from analyzer.config import Config


def validate(type: Callable, constraint: Callable) -> Callable:

    def wrapper(value):
        try:
            value = type(value)
            if not constraint(value):
                raise ArgumentTypeError(f"Value {value} doesn't meet constraints")
        except ValueError:
            raise ArgumentTypeError(f"Couldn't typecast value {value} to type {type}")

    return wrapper


"""
Type validation handlers:
"""
positive_int = validate(int, lambda x: x > 0)


def get_arg_parser(cfg: Config = None) -> ArgumentParser:

    if cfg is None:
        cfg = Config()

    parser = ArgumentParser(
        auto_env_var_prefix=cfg.ENV_VAR_PREFIX,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )

    group = parser.add_argument_group("API options")
    group.add_argument(
        "--api-host",
        default=cfg.API_HOST,
        help="IPv4/IPv6 address ANALYZER API server would listen on",
    )

    parser.add_argument(
        "--user",
        required=False,
        type=pwd.getpwnam,
        help="Linux user to be the owner of the launched process. The user is suggested to be low-privelleged",
    )

    group.add_argument(
        "--api-port",
        default=cfg.API_PORT,
        type=positive_int,
        help="TCP port ANALYZER API server would listen on",
    )
    group.add_argument(
        "--api-max-request-size",
        default=cfg.MAX_REQUEST_SIZE,
        type=positive_int,
        help="Client's max allowed request size (bytes) that ANALYZER API would be able process",
    )

    group = parser.add_argument_group("PostgreSQL options")
    group.add_argument(
        "--pg-url",
        type=URL,
        default=URL(cfg.DATABASE_URI),
        help="URL connection to the PostgreSQL database",
    )

    group = parser.add_argument_group("Logging options")
    group.add_argument(
        "--log-level",
        default=cfg.LOG_LEVEL,
        choices=("debug", "info", "warning", "error", "fatal"),
    )
    group.add_argument(
        "--log-format",
        default=cfg.LOG_FORMAT,
        choices=LogFormat.choices(),
    )

    # clear env variables after parser parsed all the necessary args
    clear_env(lambda env_var: env_var.startswith(cfg.ENV_VAR_PREFIX))

    return parser


def clear_env(rule: Callable) -> None:
    """
    Clear vulnerable environment variables such as database url connection
    """

    for name in filter(rule, tuple(os.environ)):
        os.environ.pop(name)
