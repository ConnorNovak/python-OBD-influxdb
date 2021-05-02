# -*- coding: future_fstrings -*-
# Standard modules
import pathlib

# External modules
import plac

# Local modules
from obd_influx.storage import create_recorder


@plac.annotations(
    config_json=plac.Annotation(
        "json configuration file to check",
        type=pathlib.Path)
)
def check_config_json(config_json: pathlib.Path):
    """Verify that config.json file correctly defines Recorder."""
    recorder = create_recorder(config_json=config_json)
    print(
        f"{config_json.resolve()} successfully initialized recorder")
    try:
        recorder.check_settings()
        print("recorder settings check out")
    except ImportError:
        print("recorder has no check_settings method")


if __name__ == '__main__':
    plac.call(check_config_json)
