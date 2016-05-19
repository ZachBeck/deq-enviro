# copies data from SGID to the app and makes necessary optimizations

import arcpy
import settings
from settings import fieldnames
import spreadsheet
from os import path
from build_json import parse_fields
from collections import namedtuple
import re
import shutil
from agrc import ags

commonFields = [fieldnames.ID,
                fieldnames.NAME,
                fieldnames.ADDRESS,
                fieldnames.CITY,
                fieldnames.TYPE,
                fieldnames.ENVIROAPPLABEL,
                fieldnames.ENVIROAPPSYMBOL]
logger = None
errors = []
field_type_mappings = {'Integer': 'LONG',
                       'String': 'TEXT',
                       'SmallInteger': 'SHORT'}
successes = []


def run(logr, test_layer=None):
    global logger, errors
    logger = logr

    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(3857)
    arcpy.env.geographicTransformations = 'NAD_1983_to_WGS_1984_5'

    if test_layer is None:
        admin = ags.AGSAdmin(settings.AGS_USER, settings.AGS_PASSWORD, settings.agsServer)
        admin.stopService('DEQEnviro/Secure', 'MapServer')
        admin.stopService('DEQEnviro/MapService', 'MapServer')

        logger.logMsg('deleting fgdb\n')
        shutil.rmtree(settings.fgd)
        arcpy.CreateFileGDB_management(path.dirname(settings.fgd), path.basename(settings.fgd))

    logger.logMsg('processing query layers\n')
    update_query_layers(test_layer)

    logger.logMsg('processing related tables\n')
    update_related_tables(test_layer)

    logger.logMsg('compacting file geodatabase\n')
    arcpy.Compact_management(settings.fgd)

    if test_layer is None:
        admin.startService('DEQEnviro/Secure', 'MapServer')
        admin.startService('DEQEnviro/MapService', 'MapServer')

    return errors


def update_related_tables(test_layer=None):
    global successes
    for t in spreadsheet.get_related_tables():
        name = t[fieldnames.sgidName]
        if test_layer and name != test_layer:
            continue
        try:
            if name.startswith('SGID10'):
                logger.logMsg('\nProcessing: {}'.format(name.split('.')[-1]))
                localTbl = path.join(settings.fgd, name.split('.')[-1])
                remoteTbl = path.join(settings.sgid[name.split('.')[1]], name)

                if len(validate_fields([f.name for f in arcpy.ListFields(localTbl)], t[fieldnames.fields], name)) > 0:
                    continue

                update(localTbl, remoteTbl)

                # create relationship class if missing
                rcName = t[fieldnames.relationshipName].split('.')[-1]
                rcPath = path.join(settings.fgd, rcName)
                if not arcpy.Exists(rcPath):
                    origin = path.join(settings.fgd, t[fieldnames.parentDatasetName].split('.')[-1])
                    arcpy.CreateRelationshipClass_management(origin,
                                                             localTbl,
                                                             rcPath,
                                                             'SIMPLE',
                                                             name,
                                                             t[fieldnames.parentDatasetName].split('.')[-1],
                                                             'BOTH',
                                                             'ONE_TO_MANY',
                                                             'NONE',
                                                             t[fieldnames.primaryKey],
                                                             t[fieldnames.foreignKey])
                successes.append(name)
        except:
            errors.append('Execution error trying to update fgdb with {}:\n{}'.format(name, logger.logError()))


def update(local, remote, relatedTables='table'):
    logger.logMsg('updating: {} \n    from: {}'.format(local, remote))
    if not arcpy.Exists(local):
        if arcpy.Describe(remote).dataType == 'Table':
            logger.logMsg('creating new local table')
            arcpy.CopyRows_management(remote, local)
        else:
            logger.logMsg('creating new local feature class')
            arcpy.CopyFeatures_management(remote, local)
    else:
        arcpy.TruncateTable_management(local)
        try:
            if relatedTables == 'None':
                logger.logMsg('copying instead of appending')
                arcpy.Delete_management(local)
                logger.logMsg('deleted')
                arcpy.CopyFeatures_management(remote, local)
            else:
                arcpy.Append_management(remote, local, 'NO_TEST')
        except:
            with arcpy.da.Editor(settings.fgd):
                flds = [f.name for f in arcpy.ListFields(remote)]
                logger.logMsg('append failed, using insert cursor')
                with arcpy.da.SearchCursor(remote, flds) as rcur, arcpy.da.InsertCursor(local, flds) as icur:
                    for row in rcur:
                        icur.insertRow(row)


def update_query_layers(test_layer=None):
    global successes
    for l in spreadsheet.get_query_layers():
        fcname = l[fieldnames.sgidName]
        if test_layer and fcname != test_layer:
            continue
        try:
            # update fgd from SGID
            logger.logMsg('\nProcessing: {}'.format(fcname.split('.')[-1]))
            localFc = path.join(settings.fgd, fcname.split('.')[-1])

            if fcname.startswith('SGID10'):
                remoteFc = path.join(settings.sgid[fcname.split('.')[1]], fcname)
            else:
                remoteFc = path.join(settings.dbConnects, l[fieldnames.sourceData])

            if len(validate_fields([f.name for f in arcpy.ListFields(remoteFc)], l, fcname)) > 0:
                continue

            update(localFc, remoteFc, l[fieldnames.relatedTables])

            # APP-SPECIFIC OPTIMIZATIONS
            # make sure that it has the five main fields for the fdg only
            upper_fields = [x.name.upper() for x in arcpy.ListFields(localFc)]
            for f in commonFields:
                if f not in upper_fields:
                    logger.logMsg('{} not found. Adding to {}'.format(f, localFc))

                    # get mapped field properties
                    if not l[f] == 'n/a':
                        try:
                            mappedFld = arcpy.ListFields(localFc, l[f])[0]
                        except IndexError:
                            errors.append('Could not find {} in {}'.format(l[f], fcname))
                            continue
                    else:
                        mappedFld = namedtuple('literal', 'precision scale length type')(**{'precision': 0,
                                                                                            'scale': 0,
                                                                                            'length': 50,
                                                                                            'type': 'String'})
                    arcpy.AddField_management(localFc, f, 'TEXT', field_length=255)

                # calc field
                expression = l[f]
                if not expression == 'n/a':
                    try:
                        mappedFld = arcpy.ListFields(localFc, l[f])[0]
                    except IndexError:
                        errors.append('Could not find {} in {}'.format(l[f], fcname))
                        continue
                    if mappedFld.type != 'String':
                        expression = 'str(int(!{}!))'.format(expression)
                    else:
                        expression = '!{}!.encode("utf-8")'.format(expression)
                else:
                    expression = '"{}"'.format(expression)
                arcpy.CalculateField_management(localFc, f, expression, 'PYTHON')

            apply_coded_values(localFc, l[fieldnames.codedValues])

            # scrub out any empty geometries
            arcpy.RepairGeometry_management(localFc)

            successes.append(fcname)
        except:
            errors.append('Execution error trying to update fgdb with {}:\n{}'.format(fcname,
                                                                                      logger.logError().strip()))


def validate_fields(dataFields, queryLayer, datasetName):
    msg = '{}: Could not find matches in the source data for the following fields from the query layers spreadsheet: {}'
    dataFields = set(dataFields)
    additionalFields = [queryLayer[f] for f in commonFields]
    spreadsheetFields = set([f[0] for f in parse_fields(queryLayer[fieldnames.fields])] + additionalFields) - set(['n/a'])

    invalidFields = spreadsheetFields - dataFields

    if len(invalidFields) > 0:
        er = msg.format(datasetName, ', '.join(invalidFields))
        errors.append(er)
        return er
    else:
        return []


def apply_coded_values(fc, codedValuesTxt):
    if len(codedValuesTxt.strip()) == 0:
        return

    field_name = re.search(ur'(^\S*)\:', codedValuesTxt).group(1)
    codes = re.findall(ur'(\S*) \(.*?\),', codedValuesTxt)
    descriptions = re.findall(ur'\S* \((.*?)\),', codedValuesTxt)

    logger.logMsg('applying coded values for {} field'.format(field_name))

    layer = arcpy.MakeFeatureLayer_management(fc)
    for code, desc in zip(codes, descriptions):
        arcpy.SelectLayerByAttribute_management(layer, where_clause='{} = \'{}\''.format(field_name, code))
        arcpy.CalculateField_management(fc, field_name, '"{}"'.format(desc), 'PYTHON')


if __name__ == '__main__':
    from agrc import logging
    import sys

    logger = logging.Logger()

    # first argument is optionally the SGID feature class or table name
    if len(sys.argv) == 2:
        print(run(logger, sys.argv[1]))
    else:
        print(run(logger))
    print('done')
