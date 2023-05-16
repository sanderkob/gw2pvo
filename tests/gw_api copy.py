import json
import logging
import time
from datetime import datetime
import requests

__author__ = "Mark Ruys"
__copyright__ = "Copyright 2017, Mark Ruys"
__license__ = "MIT"
__email__ = "mark@paracas.nl"

class GoodWeApi:
    '''The class interacts with the GoodWe API and retrieves data from it. 
        It has the following methods:
        init__(self, system_id, account, password):
            Initializes the class with the required parameters for accessing the GoodWe API.
        statusText(self, status):
            Returns a string representing the status of the inverter.
        calcPvVoltage(self, data):
            Calculates and returns the PV voltage.
        getCurrentReadings(self):
            Retrieves the most recent readings from the GoodWe API.
        getActualKwh(self, date):
            Retrieves the actual kWh of a given date.
        getLocation(self):
            Retrieves the location of the system.'''

    def __init__(self, system_id, account, password):
        '''Initialize a new instance of the SEMSPortal API client.
    Args:
        system_id (str): The ID of the SEMSPortal system to connect to.
        account (str): The account name to use for authentication.
        password (str): The password to use for authentication.
    Attributes:
        token (str): A JSON-encoded string representing the authentication token to use.
        global_url (str): The base URL of the SEMSPortal API.
        base_url (str): The URL of the SEMSPortal system to connect to.
    Returns:
        None.'''
        self.system_id = system_id
        self.account = account
        self.password = password
        self.token = '{"version":"v3.1","client":"ios","language":"en"}'
        self.global_url = 'https://semsportal.com/api/'
        self.base_url = self.global_url

    def statusText(self, status):
        '''Return the label corresponding to the given status code.
            Args:
                status (int): The status code.
            Returns:
                str: The label corresponding to the status code, or "Unknown" if the status code is not recognized.'''
        labels = { -1 : 'Offline', 0 : 'Waiting', 1 : 'Normal', 2: 'Fault' }
        return labels[status] if status in labels else 'Unknown'

    def calcPvVoltage(self, data):
        '''ABstract the voltages of all PV strings connected.
            Args:
                data (dict): The data containing the voltage readings for each string.
            Returns:
                float: The total voltage of the photovoltaic panels.'''
        pv_voltages = [
            data['vpv' + str(i)]
            for i in range(1, 5)
            if 'vpv' + str(i) in data
            if data['vpv' + str(i)]
            if data['vpv' + str(i)] < 6553
        ]
        return round(sum(pv_voltages)/len(pv_voltages), 1)

    def getCurrentReadings(self):
        '''Download the most recent readings from the GoodWe API and extract the relevant information.
            Returns:
                dict: A dictionary containing the following keys:
                    - 'status': The status of the inverter.
                    - 'pgrid_w': The current output power of the inverter.
                    - 'eday_kwh': The energy produced by the inverter in the current day.
                    - 'etotal_kwh': The total energy produced by the inverter.
                    - 'grid_voltage': The voltage of the electrical grid.
                    - 'pv_voltage': The total voltage of the photovoltaic panels.
                    - 'vpv1': The voltage of the first string of photovoltaic panels.
                    - 'vpv2': The voltage of the second string of photovoltaic panels.
                    - 'Ppv1': The power of the first string of photovoltaic panels.
                    - 'Ppv2': The power of the second string of photovoltaic panels.
                    - 'temperature': The temperature of the inverter.
                    - 'latitude': The latitude of the system, if available.
                    - 'longitude': The longitude of the system, if available.'''
        payload = {'powerStationId' : self.system_id}
        data = self.call("v2/PowerStation/GetMonitorDetailByPowerstationId", payload)
        result = {
            'status' : 'Unknown',
            'pgrid_w' : 0,
            'eday_kwh' : 0,
            'etotal_kwh' : 0,
            'grid_voltage' : 0,
            'pv_voltage' : 0,
            'vpv1' : 0,                 # voltage string 1
            'vpv2' : 0,                 # voltage string 2
            'Ppv1' : 0,                 # power string 1
            'Ppv2' : 0,                 # power string 
            'temperature' : data['inverter'][0]['tempperature'],  # inverter temperature (sic)
            'latitude' : data['info'].get('latitude'),
            'longitude' : data['info'].get('longitude'),
            'last_refresh' : data['inverter'][0]['last_refresh_time']
        }
        last_refresh=data['inverter'][0]['last_refresh_time']
        print (last_refresh)
        # print (result['last_refresh'])
        last_refresh = datetime.strptime(last_refresh, '%m/%d/%Y %H:%M:%S')
        print (last_refresh)
        print (last_refresh.timestamp())
        last_refresh=int(last_refresh.timestamp())
        print (last_refresh)
        count = 0
        for inverterData in data['inverter']:
            status = self.statusText(inverterData['status'])
            if status == 'Normal':
                result['status'] = status
                result['pgrid_w'] += inverterData['out_pac']
                result['grid_voltage'] += self.parseValue(inverterData['output_voltage'], 'V')
                result['pv_voltage'] += self.calcPvVoltage(inverterData['d'])
                count += 1
    #modified 20 mar 2022                
    #            result['eday_kwh'] += inverterData['eday']
    #            result['etotal_kwh'] += inverterData['etotal']
                result['eday_kwh'] += inverterData['eday']
                result['etotal_kwh'] += inverterData['etotal']
        if count > 0:
            # These values should not be the sum, but the average
            result['grid_voltage'] /= count
            result['pv_voltage'] /= count
        elif len(data['inverter']) > 0:
            # We have no online inverters, then just pick the first
            inverterData = data['inverter'][0]
            result['status'] = self.statusText(inverterData['status'])
            result['pgrid_w'] = inverterData['out_pac']
            result['grid_voltage'] = self.parseValue(inverterData['output_voltage'], 'V')
            result['pv_voltage'] = self.calcPvVoltage(inverterData['d'])
            
        result['vpv1'] = inverterData['d']['vpv1']
        result['vpv2'] = inverterData['d']['vpv2']
        result['Ppv1'] = inverterData['d']['vpv1'] * inverterData['d']['ipv1']
        result['Ppv2'] = inverterData['d']['vpv2'] * inverterData['d']['ipv2']
                    
        message = "{status}, {pgrid_w} W now, {eday_kwh} kWh today, {etotal_kwh} kWh all time, {grid_voltage} V grid, {pv_voltage} V PV, {vpv1} V PV1, {vpv2} V PV2, {Ppv1} W PV1, {Ppv2} W PV2".format(**result)
        if result['status'] == 'Normal' or result['status'] == 'Offline':
            logging.debug(message)
        else:
            logging.info(message)
        return result

    def getActualKwh(self, date):
        '''Retrieve the actual energy output (in kilowatt-hours) for a specific date from the GoodWe API
        Args:
            self (object): An instance of the GoodWe API client.
            date (datetime.date): The date for which to retrieve the energy output.
        Returns:
            float: The actual energy output in kilowatt-hours for the specified date.'''
        payload = {
            'powerstation_id' : self.system_id,
            'count' : 1,
            'date' : date.strftime('%Y-%m-%d')
        }
        data = self.call("v2/PowerStationMonitor/GetPowerStationPowerAndIncomeByDay", payload)
        if not data:
            logging.warning("GetPowerStationPowerAndIncomeByDay missing data")
            return 0
        eday_kwh = 0
        for day in data:
            if day['d'] == date.strftime('%m/%d/%Y'):
                eday_kwh = day['p']
        return eday_kwh

    def getLocation(self):
        '''Retrieve the location coordinates (latitude and longitude) of the solar power system associated with the GoodWe API client.
        Args:
            self (object): An instance of the GoodWe API client.
        Returns:
            dict: A dictionary containing the latitude and longitude coordinates of the solar power system.'''
        payload = {
            'powerStationId' : self.system_id
        }
        data = self.call("v2/PowerStation/GetMonitorDetailByPowerstationId", payload)
        if 'info' not in data:
            logging.warning(f"GetMonitorDetailByPowerstationId returned bad data: {data}")
            return {}
        return {
            'latitude' : data['info'].get('latitude'),
            'longitude' : data['info'].get('longitude'),
        }

    def getDayPac(self, date):
        '''Retrieve the power output data (in watts) for a specific date from the GoodWe API
        Args:
            self (object): An instance of the GoodWe API client.
            date (datetime.date): The date for which to retrieve the power output data.
        Returns:
            list: A list of power output data samples, each containing a timestamp and a power output value in watts.'''
        payload = {
            'id' : self.system_id,
            'date' : date.strftime('%Y-%m-%d')
        }
        data = self.call("v2/PowerStationMonitor/GetPowerStationPacByDayForApp", payload)
        if 'pacs' not in data:
            logging.warning(f"GetPowerStationPacByDayForApp returned bad data: {data}")
            return []
        return data['pacs']

    def getDayReadings(self, date):
        '''Retrieve the energy production data (in kilowatt-hours) for a specific date from the GoodWe API, 
        including the power output readings for each hour of the day
        Args:
            self (object): An instance of the GoodWe API client.
            date (datetime.date): The date for which to retrieve the energy production data.
        Returns:
            dict: A dictionary containing the location coordinates of the solar power system, 
            a list of power output readings for each hour of the day, 
            and the total energy production in kilowatt-hours for the specified date.'''
        result = self.getLocation()
        pacs = self.getDayPac(date)
        hours = 0
        kwh = 0
        result['entries'] = []
        for sample in pacs:
            parsed_date = datetime.strptime(sample['date'], "%m/%d/%Y %H:%M:%S")
            next_hours = parsed_date.hour + parsed_date.minute / 60
            pgrid_w = sample['pac']
            if pgrid_w > 0:
                kwh += pgrid_w / 1000 * (next_hours - hours)
                result['entries'].append({
                    'dt' : parsed_date,
                    'pgrid_w': pgrid_w,
                    'eday_kwh': round(kwh, 3)
                })
            hours = next_hours
        eday_kwh = self.getActualKwh(date)
        if eday_kwh > 0:
            correction = eday_kwh / kwh
            for sample in result['entries']:
                sample['eday_kwh'] *= correction
        return result

    def call(self, url, payload):
        '''Make an HTTP POST request to the GoodWe API with the specified payload and retrieve the response data.
        Args:
            self (object): An instance of the GoodWe API client.
            url (str): The URL path for the GoodWe API endpoint to call.
            payload (dict): The request payload data to send to the API.
        Returns:
            dict: The response data from the GoodWe API.'''
        for i in range(1, 4):
            try:
                headers = {
                    'User-Agent': 'SEMS Portal/3.1 (iPhone; iOS 13.5.1; Scale/2.00)',
                    'Token': self.token,
                }

                r = requests.post(self.base_url + url, headers=headers, data=payload, timeout=30)  # timeout was 10, now 30
                r.raise_for_status()
                data = r.json()
                # logging.debug(data)
                try:
                    code = int(data['code'])
                except ValueError:
                    raise Exception("Failed to call GoodWe API (no code)")
                
                if code == 0 and data['data'] is not None:
                    return data['data']
                elif code == 100001:
                    loginPayload = {
                        'account': self.account,
                        'pwd': self.password,
                    }
                    r = requests.post(self.global_url + 'v2/Common/CrossLogin', headers=headers, data=loginPayload, timeout=30) # timeout was 10, now 30
                    r.raise_for_status()
                    data = r.json()
                    if 'api' not in data:
                        raise Exception(data['msg'])
                    self.base_url = data['api']
                    self.token = json.dumps(data['data'])
                else:
                    raise Exception("Failed to call GoodWe API (code {})".format(code))
            except requests.exceptions.RequestException as exp:
                logging.warning(exp)
            time.sleep(i ** 3)
        else:
            raise Exception("Failed to call GoodWe API (too many retries)")
        return {}

    def parseValue(self, value, unit):
        '''Parse a numeric value with a specified unit and return the value as a float.
        Args:
            self (object): An instance of the GoodWe API client.
            value (str): The numeric value with unit to parse.
            unit (str): The unit of measurement for the numeric value.
        Returns:
            float: The parsed numeric value. If the value cannot be parsed, return 0.'''
        try:
            return float(value.rstrip(unit))
        except ValueError as exp:
            logging.warning(exp)
            return 0
