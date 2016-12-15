#!/usr/bin/env python
# * coding: utf8 *
'''
main.py

A module that contains the main forklift pallets for deq

Note: There is a separate scheduled task that runs this pallet for SGID10.ENVIRONMENT.DAQAirMonitorByStation
on an hourly basis.
'''

import arcpy
import build_json
import settings
import update_sgid
import update_fgdb
import update_ftp
import pystache
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from forklift.models import Pallet, Crate
from forklift.messaging import send_email
from forklift import lift
from forklift import core
from os import path

current_folder = path.dirname(__file__)
services = [('DEQEnviro/Secure', 'MapServer'),
            ('DEQEnviro/MapService', 'MapServer'),
            ('DEQEnviro/ExportWebMap', 'GPServer'),
            ('DEQEnviro/Toolbox', 'GPServer')]


def send_report_email(name, report_data):
    report_data['name'] = name
    template = path.join(path.abspath(path.dirname(__file__)), 'report_template.html')
    with open(template, 'r') as template_file:
        email_content = pystache.render(template_file.read(), report_data)

    message = MIMEMultipart()
    message.attach(MIMEText(email_content, 'html'))

    send_email(settings.reportEmail, 'DEQ Nightly Report'.format(name), message)


#: pallets are executed in alphabetical order
class DEQNightly0TempTablesPallet(Pallet):
    #: this is for source tables -> point feature classes
    #: it first copies the tables to a temp gdb
    #: then it etl's them directly into sgid
    def __init__(self, test_layer=None):
        super(DEQNightly0TempTablesPallet, self).__init__()

        self.test_layer = test_layer

    def build(self, target):
        self.add_crates(update_sgid.get_temp_crate_infos(self.test_layer))

    def process(self):
        self.log.info('ETL-ing temp tables to points in SGID...')
        update_sgid.start_etl(self.get_crates())

    def ship(self):
        send_report_email('Temp Tables', self.get_report())


class DEQNightly1SDEUpdatePallet(Pallet):
    #: this pallet assumes that the destination data already exits
    #: this is for all non-etl data updates to SGID
    def __init__(self, test_layer=None):
        super(DEQNightly1SDEUpdatePallet, self).__init__()

        self.test_layer = test_layer

    def build(self, target):
        if self.test_layer is not None:
            self.add_crates(update_sgid.get_crate_infos(self.test_layer))
        else:
            self.add_crates(update_sgid.get_crate_infos())

    def process(self):
        if settings.updateFTP:
            self.log.info('UPDATING FTP PACKAGES')
            update_ftp.run(self.log)

    def ship(self):
        send_report_email('SGID', self.get_report())


class DEQNightly2FGDBUpdatePallet(Pallet):
    #: this pallet updates the deqquerylayers.gdb from SGID
    def __init__(self, test_layer=None):
        super(DEQNightly2FGDBUpdatePallet, self).__init__()

        self.arcgis_services = services
        self.test_layer = test_layer

        self.copy_data = [settings.fgd]

    def validate_crate(self, crate):
        return update_fgdb.validate_crate(crate)

    def build(self, configuration):
        self.configuration = configuration

    def requires_processing(self):
        return True

    def process(self):
        #: This needs to happen after the crates in DEQNightly0TempTables
        #: have been processed. That's why I'm creating them and manually processing them.
        if self.test_layer is not None:
            self.add_crates(update_fgdb.get_crate_infos(self.test_layer))
        else:
            self.add_crates(update_fgdb.get_crate_infos())

        #: use Copy_management to copy a few problem tables that need to not have an OBJECTID field
        problem_tables = ['SGID10.ENVIRONMENT.DEQMAP_EIChemical']
        if not arcpy.Exists(self.get_crates()[0].destination_workspace):
            arcpy.CreateFileGDB_management(path.dirname(self.get_crates()[0].destination_workspace), path.basename(self.get_crates()[0].destination_workspace))
        for crate in self.get_crates():
            if crate.source_name in problem_tables and not arcpy.Exists(crate.destination):
                arcpy.Copy_management(crate.source, crate.destination)

        lift.process_crates_for([self], core.update, self.configuration)

        for crate in self.get_crates():
            if crate.result[0] in [Crate.CREATED, Crate.UPDATED]:
                self.log.info('post processing crate: %s', crate.destination_name)
                update_fgdb.post_process_crate(crate)

    def ship(self):
        try:
            self.log.info('BUILDING JSON FILE')
            build_json.run()
        except:
            raise
        finally:
            send_report_email('App Data', self.get_report())


class DEQNightly3ReferenceDataPallet(Pallet):
    def __init__(self, test_layer=None):
        super(DEQNightly3ReferenceDataPallet, self).__init__()

        self.test_layer = test_layer

        self.arcgis_services = services

        self.staging = 'C:\\Scheduled\\staging'
        self.sgid = path.join(self.garage, 'SGID10.sde')
        self.boundaries = path.join(self.staging, 'boundaries.gdb')
        self.water = path.join(self.staging, 'water.gdb')
        self.environment = path.join(self.staging, 'environment.gdb')

        self.copy_data = [self.boundaries,
                          self.water,
                          self.environment]

    def build(self, target):
        if self.test_layer is None:
            self.add_crate(('Counties', self.sgid, self.boundaries))
            self.add_crate(('HUC', self.sgid, self.water))
            self.add_crate(('ICBUFFERZONES', self.sgid, self.environment))
