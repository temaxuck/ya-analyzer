from aiomisc.log import basic_config


def set_logging(log_level: str, log_format: str) -> None:
    basic_config(log_level, log_format, buffered=True)
