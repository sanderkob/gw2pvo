import datetime
import csv

__author__ = "Mark Ruys"
__copyright__ = "Copyright 2017, Mark Ruys"
__license__ = "MIT"
__email__ = "mark@paracas.nl"


class GoodWeCSV:
    """ A class for appending solar inverter data to a CSV file in the GoodWe format.
    Args:
        filename (str): The path of the CSV file to append the data to. The string 'DATE'
            in the filename will be replaced with today's date in ISO format.
    Methods:
        append(data): Appends a row of solar inverter data to the CSV file. The data is
            formatted and ordered according to the GoodWe CSV format.
        format_field(value): Formats a value while respecting the locale, so that Excel opens
            the CSV properly. Floats are formatted with thousands separators.
        label(field): Returns the label of a solar inverter data field according to the
            GoodWe CSV format.
        order(): Returns the order of the solar inverter data fields according to the
            GoodWe CSV format."""

    def __init__(self, filename):
        self.filename = filename.replace('DATE', datetime.date.today().isoformat())

    def append(self, data):
        ''' Append a row to the CSV file. '''
        try:
            with open(self.filename, 'x', newline='') as csvfile:
                csvfile.write('\ufeff')  # Add UTF-8 BOM header
                csvwriter = csv.writer(csvfile, dialect='excel', delimiter=';')
                csvwriter.writerow([self.label(field) for field in self.order()])
        except:
            pass

        with open(self.filename, 'a', newline='') as csvfile:
            csvwriter = csv.writer(csvfile, dialect='excel', delimiter=';')
            csvwriter.writerow([self.format_field(data[field]) for field in self.order()])

    def format_field(self, value):
        ''' Format values while respecting the locale, so Excel opens the CSV properly. '''
        if type(value) is float:
            return "{:n}".format(value)
        if type(value) is list:
            return "/".join([self.format_field(v) for v in value])
        return value

    def label(self, field):
        return {
            'status': 'Status',
            'pgrid_w': 'Power (W)',
            'eday_kwh': 'Energy today (kWh)',
            'etotal_kwh': 'Energy total (kWh)',
        }[field]

    def order(self):
        return [
            'status',
            'pgrid_w',
            'eday_kwh',
            'etotal_kwh',
        ]
