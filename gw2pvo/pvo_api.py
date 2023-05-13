import logging
import time
import requests

__author__ = "Mark Ruys"
__copyright__ = "Copyright 2017, Mark Ruys"
__license__ = "MIT"
__email__ = "mark@paracas.nl"


class PVOutputApi:
    """A class to interact with the PVOutput API in order to upload energy production and consumption data.
    The class has methods to add current system status and historical daily data to the PVOutput database. 
    The constructor takes in a system_id and api_key which are used for authentication to the PVOutput API.
    The add_status method takes in various data points such as power produced and consumed, temperature, voltage, 
        and user-defined data and uploads it to the PVOutput database. 
    The add_day method takes in daily data as a list of dictionaries, and sends it to the PVOutput database in batches of 30.
    The call method is a helper function used to make HTTP requests to the PVOutput API. 
        It sets the necessary headers for authentication and handles error cases, such as rate limiting and server errors."""

    def __init__(self, system_id, api_key):
        self.m_system_id = system_id
        self.m_api_key = api_key

    def add_status(self, sun_up, generated_power, generated_energy, consumed_energy, consumed_power, temperature, voltage, inverter_temperature, v8_data, vpv1, vpv2, Ppv1, Ppv2, export_power, import_power):
        '''adds smart meter data to the PVOutput database through a HTTP POST request. 
        If the sun is up, the function adds additionally energy production, inverter temperature, AC voltage and string voltage and power. 
        Export_power and import_power are uploaded with n=1 to let PVoutput.org smoothen the generated_energy data,
        see https://pvoutput.org/help/api_specification.html#net-data
        The function returns nothing.'''
        # inline function to round if not None
        def r(x): return round(x) if x else None
        t = time.localtime()
        if sun_up:
            payload = {
                'd': "{:04}{:02}{:02}".format(t.tm_year, t.tm_mon, t.tm_mday),
                't': "{:02}:{:02}".format(t.tm_hour, t.tm_min),
                'v1': r(generated_energy),
                'v2': r(generated_power),
                'v3': r(consumed_energy),
                'v4': r(consumed_power),
                'v9': r(vpv1),
                'v10': r(vpv2),
                'v11': r(Ppv1),
                'v12': r(Ppv2)
            }
            # v5 is reserved for temperature, the outside temperature is derived from OpenWeatherMap through automatic upload in pvoutput
            if voltage is not None:
                payload['v6'] = voltage
            if inverter_temperature is not None:
                payload['v7'] = inverter_temperature

        else:
            payload = {
                'd': "{:04}{:02}{:02}".format(t.tm_year, t.tm_mon, t.tm_mday),
                't': "{:02}:{:02}".format(t.tm_hour, t.tm_min),
                'v3': r(consumed_energy),
                'v4': r(consumed_power)
            }

        if v8_data is not None:
            payload['v8'] = v8_data
# 
        # self.call("https://pvoutput.org/service/r2/addstatus.jsp", payload)
        logging.info(payload)

        # if sun_up:
        #     payload = {
        #         'd': payload['d'],
        #         't': payload['t'],
        #         'n' :1,
        #         'v1': r(generated_energy),
        #         'v2': r(export_power),
        #         'v4': r(import_power)
        #     }
        #     self.call("https://pvoutput.org/service/r2/addstatus.jsp", payload)
        #     logging.debug(payload)

    def add_day(self, data):
        '''adds day data to the PVOutput system in batches of 30. 
        The `data` parameter is a list of dictionaries containing the day's data. 
        Each dictionary has the following keys: `dt`, `eday_kwh`, and `pgrid_w`. 
            `dt` is a datetime object representing the timestamp of the reading, 
            `eday_kwh` is the energy generated in kWh, 
            `pgrid_w` is the power output in watts.
        The function splits the data into batches of 30 readings and converts each reading 
        into a string in the format required by PVOutput. 
        The batch of readings is then sent to the `addbatchstatus.jsp` API endpoint of PVOutput.'''

        # Send day data in batches of 30.

        for chunk in [data[i:i + 30] for i in range(0, len(data), 30)]:

            readings = []
            for reading in chunk:
                dt = reading['dt']
                fields = [
                    dt.strftime('%Y%m%d'),
                    dt.strftime('%H:%M'),
                    str(round(reading['eday_kwh'] * 1000)),
                    str(reading['pgrid_w'])
                ]
                readings.append(",".join(fields))

            payload = {
                'data': ";".join(readings)
            }
            self.call(
                "https://pvoutput.org/service/r2/addbatchstatus.jsp", payload)

    def call(self, url, payload):
        '''makes a call to the PVOutput API using the provided URL and payload. 
        It handles potential errors, rate limiting, and retries.
        Args:
            url (str): The URL to call.
            payload (dict): The data to send in the request.
        Returns:
            None.'''
        # logging.debug(payload)

        headers = {
            'X-Pvoutput-Apikey': self.m_api_key,
            'X-Pvoutput-SystemId': self.m_system_id,
            'X-Rate-Limit': '1'
        }
        for i in range(1, 4):
            try:
                r = requests.post(url, headers=headers,
                                  data=payload, timeout=10)
                if 'X-Rate-Limit-Reset' in r.headers:
                    reset = round(
                        float(r.headers['X-Rate-Limit-Reset']) - time.time())
                else:
                    reset = 0
                if 'X-Rate-Limit-Remaining' in r.headers:
                    if int(r.headers['X-Rate-Limit-Remaining']) < 10:
                        logging.warning(
                            f"Only {r.headers['X-Rate-Limit-Remaining']} requests left, reset after {reset} seconds")
                logging.debug(f'status code {r.status_code}')
                if r.status_code == 403:
                    logging.warning(f"Forbidden: {r.reason}")
                    time.sleep(reset + 1)
                else:
                    r.raise_for_status()
                    break
            except requests.exceptions.RequestException as arg:
                logging.warning(r.text or str(arg))
            # pause to prevent from making too many requests too quickly
            time.sleep(i ** 3)
        else:
            logging.error('Failed to call PVOutput API')
