import logging
import pathlib
import time
import plac
from obd_influx.scanner import Scanner


@plac.annotations(
    config_file=plac.Annotation(
        "obd_influx configuration .json file",
        type=pathlib.Path),
    log_level=plac.Annotation(
        "log level for obd logger", "option", "ll",
        type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL'])
)
def main(config_file: pathlib.Path, log_level: str = 'INFO'):
    logging.getLogger('obd').setLevel(getattr(logging, log_level))
    scanner = Scanner.init_from_config_file(config_file)
    if not scanner.is_connected:
        return  # Failed to connect on startup.

    scanner.start()
    while True:
        try:
            time.sleep(1)
            print("waiting for Ctrl-C")
        except KeyboardInterrupt:
            scanner.shutdown()
            break


if __name__ == '__main__':
    plac.call(main)
