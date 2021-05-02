# -*- coding: future_fstrings -*-
# Standard modules
import json
import logging
import pathlib
import threading
import time
from typing import Any, Dict, List, Optional, Union

# External modules
import obd

# Local modules
from obd_influx.storage import create_recorder
from obd_influx import converter

logger = logging.getLogger(__name__)

OBD_MAX_FREQUENCY = 100.0  # Hz
OBD_DEFAULT_FREQUENCY = 10.0  # Hz


class Scanner:
    """Scanners request readings from an OBD device, format them, and
    pass them to a Recorder for storage. The storage type backing the Recorder
    is determined by recorder_config['name'].
    """
    def __init__(
        self,
        portstr: str,
        baudrate: float,
        commands: List[obd.OBDCommand],
        recorder_config: Union[pathlib.Path, Dict[str, Any]],
        frequency: Optional[float] = None
    ):
        """Set up OBD connection to vehicle.

        Args:
            portstr: path to OBD device serial port
            baudrate: baudrate of OBD connection
            commands: list of obd.OBDCommands to request from vehicle
            recorder_config: configuration used to instantiate Recorder
            frequency: query frequency for each command
                if not provided, queries as fast as possible
        """
        if isinstance(recorder_config, pathlib.PurePath):
            self._recorder = create_recorder(config_json=recorder_config)
        else:
            self._recorder = create_recorder(**recorder_config)

        # Check input args
        if len(commands) <= 0:
            raise ValueError(f"No commands provided")
        bad_cmds = [c for c in commands if not isinstance(c, obd.OBDCommand)]
        if len(bad_cmds) > 0:
            raise ValueError(f"commands arg contains bad commands {bad_cmds}")

        self._commands = commands
        self._portstr = portstr
        self._baudrate = baudrate
        self.frequency = frequency

        # Set up attributes to support scanning thread
        self._e_shutdown = threading.Event()  # event used to stop scan thread
        self._scan_thread = None  # type: Optional[threading.Thread]

        self.connect()

    @classmethod
    def init_from_config_file(cls, config_file: pathlib.Path):
        with config_file.open('r') as file_handle:
            obd_config = json.load(file_handle)

        frequency = obd_config['frequency'] if 'frequency' in obd_config else None
        commands = []
        for cmd in obd_config['commands']:
            try:
                commands.append(getattr(obd.commands, cmd))
            except AttributeError:
                raise ValueError(f"obd.OBDCommand.{cmd} is not valid.")

        return cls(
            portstr=obd_config['portstr'],
            baudrate=obd_config['baudrate'],
            commands=commands,
            recorder_config=config_file,
            frequency=frequency
        )

    # Public API

    def connect(self) -> None:
        """Connects to OBD device."""
        logger.debug(
            f"Trying to connect to {self._portstr} at {self._baudrate} Hz.")
        self.obd_connection = obd.OBD(self._portstr, self._baudrate)
        logger.debug("Connected successfully")

    def disconnect(self) -> None:
        """Disconnects from OBD device."""
        if not self.is_connected:
            logger.error("Scanner not connected to OBD device")
        self.obd_connection.close()

    def start(self) -> None:
        """Start logging data in separate thread."""
        if self.is_scanning:
            logger.error("Scanner already started")
            return

        self._scan_thread = threading.Thread(
            target=self._scan_loop, name="scanner")
        self._scan_thread.daemon = True
        self._e_shutdown.clear()
        self._scan_thread.start()

    def stop(self) -> None:
        """Stop logging data and join scanning thread."""
        if not self.is_scanning:
            logger.error("Scanner not started")
            return
        self._e_shutdown.set()
        if self._scan_thread is not None:
            self._scan_thread.join()

    def shutdown(self) -> None:
        """Ensures all connections close gracefully."""
        if self.is_scanning:
            self.stop()
        if self.is_connected:
            self.disconnect()
        self._recorder.close()

    # Getters & Setters

    @property
    def frequency(self) -> float:
        """Getter for scanner query frequency."""
        return 1.0 / self._loop_time

    @frequency.setter
    def frequency(self, value: Optional[float]) -> None:
        """Setter for scanner query frequency."""
        if value is None:
            value = OBD_DEFAULT_FREQUENCY
        elif value <= 0.0:
            raise ValueError(f"desired frequency {value} <= 0.0")
        self._loop_time = 1.0 / value

    @property
    def is_connected(self) -> bool:
        """Check if scanner is connected to vehicle."""
        return self.obd_connection.is_connected()

    @property
    def is_scanning(self) -> bool:
        """Check if scanner is actively recording from vehicle."""
        return self._scan_thread is not None and self._scan_thread.is_alive()

    # Private methods

    def _get_response(
            self, command: obd.OBDCommand) -> Optional[obd.OBDResponse]:
        """Return raw response from obd command.

        Returns:
            obd.OBDResponse if response is valid, else None.
        """
        response = self.obd_connection.query(command)
        if response.is_null():
            response = None
        return response

    def _record_data(self, response: obd.OBDResponse) -> None:
        """Format OBDResponse and pass to recorder."""
        packet = converter.get_packet(response)
        self._recorder.record(packet)

    def _scan_loop(self) -> None:
        """Mainloop; request & log data from OBD device until stop() called."""
        logger.info("Scanner started")
        cmd_ndx = 0
        ctrl_c_count = 0
        while not self._e_shutdown.is_set():
            try:
                time.sleep(self.frequency)
                response = self._get_response(self._commands[cmd_ndx])
                if response is None:
                    logger.warning(
                        f"Command {self._commands[cmd_ndx]} returned None")
                else:
                    self._record_data(response)
                cmd_ndx = (cmd_ndx) + 1 % len(self._commands)
            except KeyboardInterrupt:
                break

        logger.info("Scanner stopped.")
