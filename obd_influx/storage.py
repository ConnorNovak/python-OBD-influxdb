# -*- coding: future_fstrings -*-
# Standard modules
import abc
import json
import pathlib
import time
from typing import Any, Callable, Dict, List, Optional, Union, Type

# External modules
import influxdb
import obd

Command = Union[obd.OBDCommand, obd.OBDResponse, str]  # Command type

class AbstractRecorder(abc.ABC):
    """Abstract API for record storage interface classes.

    Subclasses should implement """

    @abc.abstractclassmethod
    def init_from_json(self, config_json: pathlib.Path):
        """Initialize recorder from config.json file."""
        pass

    @abc.abstractclassmethod
    def record(self, data: Any) -> None:
        """Record provided data."""
        pass

    @abc.abstractclassmethod
    def close(self) -> None:
        """Close any persistent connections."""
        pass


_RECORDERS = {}  # type: Dict[str, Type[AbstractRecorder]]


class InfluxDBRecorder:
    """Standard data recording interface wrapper for InfluxDB."""

    def __init__(
        self, host: str, port: int, database: str,
        username: str, password: str
    ):
        """Load configuration into InfluxDBClient."""

        self._client = influxdb.InfluxDBClient(
            host=host,
            port=port,
            username=username,
            password=password,
        )
        self._client.switch_database(database)

    @classmethod
    def init_from_json(cls, config_json: pathlib.Path):
        """Initialize InfluxDBRecorder from config.json file."""
        with config_json.open('r') as io_wrapper:
            config = json.load(io_wrapper)

        if 'influx' not in config:
            raise ValueError(
                f"config.json has no top-level tag 'influx'")

        missing_keys = [
            key for key in ['host', 'port', 'database', 'username', 'password']
            if key not in config['influx']]
        if len(missing_keys) > 0:
            raise ValueError(
                f"config.json 'influx' entry missing keys {missing_keys}")
        return cls(**config['influx'])

    def record(self, data: str) -> None:
        """Wrapper for influx_write_api.write()."""
        self._client.write_points(data)

    def close(self) -> None:
        """Wrapper for influx_write_api.close()."""
        self._client.close()

    def check_settings(self) -> None:
        """Run various tests on InfluxDB."""
        self._client.ping()  # Check that InfluxDB is connected
        print("InfluxDB server pinged successfully")

        # Check that provided database exists



_RECORDERS['influxdb'] = InfluxDBRecorder


def create_recorder(
    name: Optional[str] = None, config_json: Optional[pathlib.Path] = None, **kwargs) -> AbstractRecorder:
    """Minimal 'factory' function for data recorders.

    Allows recorder 'type' to be stored as standard string, rather than
    the specific class name.

    Args:
        name: key for registered Recorder
            if none, reads 'name' from config_json
        **kwargs: used to instantiate desired Recorder

    Returns:
        instantiated Recorder instance
    """
    if name is None:
        # Read name from config.json file
        if config_json is not None:
            with config_json.open('r') as io_wrapper:
                config_dict = json.load(io_wrapper)
                try:
                    recorder_key = config_dict.pop('name')
                except KeyError as err:
                    raise KeyError(
                        "'config_json' file does not specify 'name'.") from err
        else:
            raise TypeError(
                "Must provided either 'name' or 'config_json'")
    else:
        recorder_key = name

    if recorder_key not in _RECORDERS.keys():
        raise KeyError(
            f"No recorder registered with {recorder_key}. "
            + f"Available recorders are {','.join(_RECORDERS.keys())}.")

    recorder = _RECORDERS[recorder_key]
    if config_json is None:
        return recorder(**config_dict)
    return recorder.init_from_json(config_json)


class InfluxPacketBuilder:
    """Class interface for creating influx measurements."""
    
    def __init__(self, measurement: Optional[str] = None):
        """Initialize builder (start packet if measurement given).

        Args:
            measurement: name of measurement
                starts packet if given
        """
        if measurement is None:
            self._packet = None
        else:
            self.start_packet(measurement)

    def start_packet(self, measurement: str) -> None:
        """Clear object contents and start new packet with given measurement.

        Args:
            measurement: name of measurement

        """
        self._packet = {
            'measurement': measurement,
            'time': None,
            'tags': {},
            'fields': {},
            }

    def add_tags(
        self, tags: Union[str, List[str]], values: Union[Any, List[Any]]
    ) -> None:
        """Add tags to packet.

        Args:
            tags: tag name or list of tag names
            values: tag value or list of tag values

        Raises:
            TypeError if lengths of tags and values aren't equal
            ValueError if value mismatches current influx schema
                ex. storing an integer in a string tag
        """
        #TODO (connor) Check validity of value for tag
        if isinstance(tags, str):
            tags = [tags]
        if isinstance(values, str):
            values = [values]
        if not len(tags) == len(values):
            raise TypeError(
                f"different numbers of tags and values")

        for tag, value in zip(tags, values):
            self._packet['tags'][tag] = value

    def add_fields(
        self, fields: Union[str, List[str]], values: Union[Any, List[Any]]
    ) -> None:
        """Add fields to packet.

        Args:
            fields: field name or list of field names
            values: field value or list of field values

        Raises:
            TypeError if lengths of fields and values aren't equal
            ValueError if value mismatches current influx schema
                ex. storing an integer in a string field
        """
        #TODO (connor) Check validity of value for field
        if isinstance(fields, str):
            fields = [fields]
        if isinstance(values, str):
            values = [values]
        if not len(fields) == len(values):
            raise TypeError(
                f"different numbers of fields and values")

        for field, value in zip(fields, values):
            self._packet['fields'][field] = value

    def add_timestamp(self, tstamp: Optional[float] = None) -> None:
        """Timestamp packet.

        Args:
            tstamp: timestamp to use (seconds)
                if not provided, uses time.time()
        """
        if tstamp is None:
            tstamp = time.time()
        self._packet['time'] = int(tstamp * 1e9)

    def to_json(self) -> str:
        """Converts current packet into JSON.

        Raises:
            ValueError if packet is not fully formed.
        """
        if self._packet is None:
            raise RuntimeError("Packet not started with start_packet()")

        assert self._packet['measurement'] is not None  # Should never happen

        if self._packet['time'] is None:
            raise RuntimeError("Packet was not timestamped with add_timestamp()")

        if len(self._packet['fields']) == 0:
            raise RuntimeError("Packet has no fields added with add_fields()")

        return json.dumps(self._packet)

    @property
    def timestamp(self) -> Optional[float]:
        """Returns current packet's timestamp."""
        if self._packet is None:
            return None
        return self._packet['time']

    @property
    def measurement(self) -> Optional[str]:
        """Returns current packet's measurement name."""
        if self._packet is None:
            return None
        return self._packet['measurement']


def obd_2_influx_dtc(response: obd.OBDResponse) -> str:
    """Convert OBDResponse from Dagnostic Trouble Code command."""
    raise NotImplementedError("Multi-measurement commands not supported yet")

def obd_2_influx_float(response: obd.OBDResponse) -> str:
    """Convert OBDResponse with float value to InfluxDB packet."""
    builder = InfluxPacketBuilder(measurement=response.command.name)
    builder.add_timestamp(response.time)
    builder.add_fields('value', response.value.magnitude)
    return builder.to_json()

def obd_2_influx_percent(response: obd.OBDResponse) -> str:
    """Convert OBDResponse with percent value."""
    builder = InfluxPacketBuilder(measurement=response.command.name)
    builder.add_timestamp(response.time)
    builder.add_fields('percent', response.value.magnitude)
    return builder.to_json()

def obd_2_influx_status(response: obd.OBDResponse) -> str:
    """Convert OBDResponse from status command."""
    raise NotImplementedError("Multi-measurement commands not supported yet")


FactoryKey = Union[obd.OBDCommand, obd.OBDResponse, str]


class InfluxDBConverterFactory:
    """Class interface for serializing OBDResponses.""" 

    def __init__(self):
        self._converters = {}  # type: Dict[str, Callable]

    def register(self, command: FactoryKey, converter: Callable) -> None:
        """Register new converter for command.

        Args:
            command: OBDCommand, OBDResponse, or command name
            converter: function to convert command to influx packet

        Raise:
            ValueError if command already has registered converter
        """
        key = self._convert_to_key(command)
        if key in self._converters:
            raise ValueError(
                f"converter already registered for command {key}")

        self._converters[key] = converter

    def get_converter(self, command: Command) -> Callable:
        """Get converter for given command.

        Args:
            command: OBDCommand, OBDResponse, or command name

        Raise:
            KeyError if no converter registered for command
        """
        key = self._convert_to_key(command)
        if key not in self._converters:
            raise KeyError(f"No converter registered for command {key}")
        return self._converters[key]

    def get_packet(self, response: obd.OBDResponse, *args, **kwargs) -> str:
        """Convert given obd response with registered converter.

        Args:
            response: obd.OBDResponse from OBD device
            *args, **kwargs passed to converter

        Returns:
            output from converter registered to provided response
        """
        converter = self.get_converter(response)
        return converter(response, *args, **kwargs)

    @staticmethod
    def _convert_to_key(command: Command) -> str:
        """Convert OBDCommand, OBDResponse, or str to converter key."""
        if isinstance(command, obd.OBDResponse):
            command = command.command.name

        if isinstance(command, obd.OBDCommand):
            command = command.name

        elif isinstance(command, str):
            if not obd.commands.has_name(command):
                raise ValueError(f"obd.command has no command {command}")

        return command
