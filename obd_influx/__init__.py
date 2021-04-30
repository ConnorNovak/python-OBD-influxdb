# Standard modules
import logging

import obd.commands
import obd_influx.storage as storage

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

converter = storage.InfluxDBConverterFactory()

# Percentage commands
_callback = storage.obd_2_influx_percent
converter.register(obd.commands.ACCELERATOR_POS_E, _callback)

# Percentage commands
_callback = storage.obd_2_influx_float
converter.register(obd.commands.COOLANT_TEMP, _callback)
converter.register(obd.commands.DTC_BAROMETRIC_PRESSURE, _callback)
converter.register(obd.commands.DTC_INTAKE_TEMP, _callback)
converter.register(obd.commands.DTC_RUN_TIME, _callback)
converter.register(obd.commands.ELM_VOLTAGE, _callback)
converter.register(obd.commands.RPM, _callback)
converter.register(obd.commands.RUN_TIME, _callback)

# DTC commands
_callback = storage.obd_2_influx_dtc
converter.register(obd.commands.FREEZE_DTC, _callback)
converter.register(obd.commands.GET_DTC, _callback)

# Status commands
_callback = storage.obd_2_influx_status
converter.register(obd.commands.STATUS, _callback)
