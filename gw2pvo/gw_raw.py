import datetime
import csv
from pathlib import Path

__author__ = "Mark Ruys"
__copyright__ = "Copyright 2017, Mark Ruys"
__license__ = "MIT"
__email__ = "mark@paracas.nl"


class RawCSV:
    """ A class for appending raw solar inverter data and smart meter data to a CSV file.
    Args:
        filename (str): The path of the CSV file to append the data to. The string 'DATE'
            in the filename will be replaced with today's date in ISO format.
    Methods:
        append(data): Appends a row of data to the CSV file. The data is
            formatted and ordered according to the Excel CSV format.
        format_field(value): Formats a value while respecting the locale, so that Excel opens
            the CSV properly. Floats are formatted with thousands separators.
        label(field): Returns the label of a solar inverter data field according to the
            GoodWe CSV format.
        order(): Returns the order of the solar inverter data fields according to the
            PVoutput CSV format."""

    def __init__(self, filename):
        # construct filename with absolute path and isoformat date without dash
        self.filename = str(Path(__file__).parent.resolve()) + '/' + filename.replace(
            'DATE', datetime.date.today().strftime("%Y%m%d")) + '.csv'

    def append(self, data):
        ''' Append a row to the CSV file. '''
        try:
            # encoding='utf-8-sig' adds a UTF-8 BOM header for Windows Excel
            with open(self.filename, 'x', newline='', encoding='utf-8-sig') as csvfile:
                csvwriter = csv.writer(csvfile, dialect='excel', delimiter=';')
                csvwriter.writerow([self.label(field)
                                   for field in self.order()])
        except:
            pass

        with open(self.filename, 'a', newline='') as csvfile:
            csvwriter = csv.writer(csvfile, dialect='excel', delimiter=';')
            csvwriter.writerow([self.format_field(data[field])
                               for field in self.order()])

    def format_field(self, value):
        ''' Format values while respecting the locale, so Excel opens the CSV properly. '''
        if type(value) is float:
            return "{:n}".format(value)
        if type(value) is list:
            return "/".join([self.format_field(v) for v in value])
        return value

    def label(self, field):
        return {
            'd': 'date',
            't': 'time',
            'generated_energy': 'Energy',
            'generated_power': 'Power',
            'consumed_energy': 'Energy Used',
            'consumed_power': 'Power Used',
            'import_energy': 'Imported Energy',
            'import_power': 'Imported Power',
            'export_energy': 'Exported Energy',
            'export_power': 'Exported Power'
        }[field]

    def order(self):
        return [
            'd',
            't',
            'generated_energy',
            'generated_power',
            'consumed_energy',
            'consumed_power',
            'import_energy',
            'import_power',
            'export_energy',
            'export_power'
        ]
