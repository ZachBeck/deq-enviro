#!/usr/bin/env python
# * coding: utf8 *
'''
hourly.py

A script to update DAQ data that needs to be updated hourly.
SGID10.ENVIRONMENT.DAQAirMonitorByStation
'''


from forklift import core
from forklift.messaging import send_email
from forklift.models import Crate
from os import path
from traceback import format_exc
from update_fgdb import validate_crate
from settings.dev import reportEmail
import logging.config
from logging import shutdown
import settings
from forklift.__main__ import log_location, detailed_formatter
from os import makedirs
import sys


def _setup_logging():
    # copied from forklift
    log = logging.getLogger('deqhourly')

    log.logThreads = 0
    log.logProcesses = 0

    debug = 'DEBUG'

    try:
        makedirs(path.dirname(log_location))
    except:
        pass

    file_handler = logging.handlers.RotatingFileHandler(log_location.replace('forklift.log', 'deqhourly.log'), backupCount=18)
    file_handler.doRollover()
    file_handler.setFormatter(detailed_formatter)
    file_handler.setLevel(debug)

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(detailed_formatter)
    console_handler.setLevel(debug)

    log.addHandler(file_handler)
    log.addHandler(console_handler)
    log.setLevel(debug)

    return log


try:
    sgid_name = 'DAQAirMonitorData'
    sgid_db = settings.sgid['ENVIRONMENT']
    stage_db = r'C:\Scheduled\staging\deqquerylayers.gdb'
    source_db = path.join(settings.dbConnects, r'AVData.sde')
    source_name = 'AVData.dbo.interactive_map_monitoring_data'
    bad_results = [Crate.UNHANDLED_EXCEPTION, Crate.UNINITIALIZED]

    log = _setup_logging()

    log.info('creating crates')
    sde_update_crate = Crate(source_name, source_db, sgid_db, sgid_name, source_primary_key='EPAID')
    fgdb_update_crate1 = Crate(sgid_name, sgid_db, path.join(settings.mapData1, 'deqquerylayers.gdb'), sgid_name)
    fgdb_update_crate2 = Crate(sgid_name, sgid_db, path.join(settings.mapData2, 'deqquerylayers.gdb'), sgid_name)
    stage_update_crate = Crate(sgid_name, sgid_db, stage_db, sgid_name)

    log.info('processing sde crate')
    core.init(log)
    sde_update_crate.set_result(core.update(sde_update_crate, validate_crate))
    log.info('processing fgdb crate')
    fgdb_update_crate1.set_result(core.update(fgdb_update_crate1, validate_crate))
    fgdb_update_crate2.set_result(core.update(fgdb_update_crate2, validate_crate))
    log.info('processing staging crate')
    stage_update_crate.set_result(core.update(stage_update_crate, validate_crate))

    if sde_update_crate.result[0] in bad_results or fgdb_update_crate1.result in bad_results or fgdb_update_crate2.result in bad_results:
        send_email(reportEmail,
                   'DEQ Hourly Crate Error',
                   'SDE Update Crate:\n{}\n\nFGDB Update Crates:\n{}\n{}'.format(sde_update_crate, fgdb_update_crate1, fgdb_update_crate2))
except Exception as e:
    log.error(format_exc())
    send_email(reportEmail, 'DEQ Hourly Script Error', format_exc())
finally:
    shutdown()
