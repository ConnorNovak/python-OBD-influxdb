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
    type_ = 'influxdb'
    recorder = create_recorder(type_, config_json)
    print(
        f"{config_json.resolve()} successfully initialized {type_} recorder")
    recorder.check_settings()
    print(f"{type_} recorder settings check out")
    print(f"{type_} recorder has no check_settings method")


if __name__ == '__main__':
    plac.call(check_config_json)
