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
        '''upload format (using extended data v7-v12):
        data['pgrid_w']            v1 power produced
        last_eday_wh               v2 energy produced
        cons_wh                    v3 energy consumed
        cons_w                     v4 power consumed
        data.get('temperature')    v5 dummy (outside temperature from OpenWeatherMap)
        voltage                    v6 line voltage
        data['temperature']        v7 inverter temperature
        v8data              v8 user defined data from MQTT
        data['vpv1']               v9 voltage string 1
        data['vpv2']               v10 voltage string 2
        data['Ppv1']               v11 power string 1
        data['Ppv2']               v12 power string2'''

    def add_status(self, SunUp, pgrid_w, eday_wh, cons_wh, cons_w, temperature, voltage, invertertemp, v8data, vpv1, vpv2, Ppv1, Ppv2):
        '''adds solar power system data to the PVOutput database through a HTTP POST request. 
        The data allways include date, time and energy consumption.
        If the sun is up, the function adds additionally energy production, inverter temperature, AC voltage and string voltage and power.
        The function returns nothing.'''   
        t = time.localtime()        
        if SunUp:
            payload = {
                'd' : "{:04}{:02}{:02}".format(t.tm_year, t.tm_mon, t.tm_mday),
                't' : "{:02}:{:02}".format(t.tm_hour, t.tm_min),
                'v1' : round(eday_wh),
                'v2' : round(pgrid_w),
                'v3' : round(cons_wh)  if cons_wh else None,
                'v4' : round(cons_w)  if cons_w else None,
                'v9' : round(vpv1) if vpv1 else None,
                'v10' : round(vpv2) if vpv2 else None,
                'v11' : round(Ppv1) if Ppv1 else None,
                'v12' : round(Ppv2) if Ppv2 else None
            }
            # v5 is reserved for temperature, the outside temperature is derived from OpenWeatherMap through automatic upload in pvoutput
            if voltage is not None:
                payload['v6'] = voltage
            if invertertemp is not None:
                payload['v7'] = invertertemp
            if v8data is not None:
                payload['v8'] = v8data
        else:
            payload = {
                'd' : "{:04}{:02}{:02}".format(t.tm_year, t.tm_mon, t.tm_mday),
                't' : "{:02}:{:02}".format(t.tm_hour, t.tm_min),       
                'v3' : round(cons_wh)  if cons_wh else None,
                'v4' : round(cons_w)  if cons_w else None
            }                          
        #        print(payload) 
        self.call("https://pvoutput.org/service/r2/addstatus.jsp", payload)

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
                'data' : ";".join(readings)
            }           
            self.call("https://pvoutput.org/service/r2/addbatchstatus.jsp", payload)

    def call(self, url, payload):
        '''makes a call to the PVOutput API using the provided URL and payload. 
        It handles potential errors, rate limiting, and retries.
        Args:
            url (str): The URL to call.
            payload (dict): The data to send in the request.
        Returns:
            None.'''      
        logging.debug(payload)

        headers = {
            'X-Pvoutput-Apikey' : self.m_api_key,
            'X-Pvoutput-SystemId' : self.m_system_id,
            'X-Rate-Limit': '1'
        }
        for i in range(1, 4):
            try:
                r = requests.post(url, headers=headers, data=payload, timeout=10)
                if 'X-Rate-Limit-Reset' in r.headers:
                    reset = round(float(r.headers['X-Rate-Limit-Reset']) - time.time())
                else:
                    reset = 0
                if 'X-Rate-Limit-Remaining' in r.headers:
                    if int(r.headers['X-Rate-Limit-Remaining']) < 10:
                        logging.warning(f"Only {r.headers['X-Rate-Limit-Remaining']} requests left, reset after {reset} seconds")
                if r.status_code == 403:
                    logging.warning(f"Forbidden: {r.reason}")
                    time.sleep(reset + 1)
                else:
                    r.raise_for_status()
                    break
            except requests.exceptions.RequestException as arg:
                logging.warning(r.text or str(arg))
            time.sleep(i ** 3)      #  pause to prevent from making too many requests too quickly
        else:
            logging.error("Failed to call PVOutput API")

