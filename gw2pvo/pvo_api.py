import logging
import time
import requests

__author__ = "Mark Ruys"
__copyright__ = "Copyright 2017, Mark Ruys"
__license__ = "MIT"
__email__ = "mark@paracas.nl"

class PVOutputApi:

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
        received_data              v8 user defined data from MQTT
        data['vpv1']               v9 voltage string 1
        data['vpv2']               v10 voltage string 2
        data['Ppv1']               v11 power string 1
        data['Ppv2']               v12 power string2
        '''
    def add_status(self, SunUp, pgrid_w, eday_wh, cons_wh, cons_w, temperature, voltage, invertertemp, received_data, vpv1, vpv2, Ppv1, Ppv2):
        t = time.localtime()        
        if SunUp:
            payload = {
                'd' : "{:04}{:02}{:02}".format(t.tm_year, t.tm_mon, t.tm_mday),
                't' : "{:02}:{:02}".format(t.tm_hour, t.tm_min),
                'v1' : round(eday_wh),
                'v2' : round(pgrid_w),
                'v3' : round(cons_wh),
                'v4' : round(cons_w),
                'v9' : round(vpv1),
                'v10' : round(vpv2),
                'v11' : round(Ppv1),
                'v12' : round(Ppv2)
            }
            # v5 is not used, the outside temperature is derived from OpenWeatherMap through automatic upload in pvoutput
            # v5 can be used for other payload
            # if dummy is not None:
            #     payload['v5'] = dummy
            if voltage is not None:
                payload['v6'] = voltage
            if invertertemp is not None:
                payload['v7'] = invertertemp
            if received_data is not None:
                payload['v8'] = received_data
        else:
            payload = {
                'd' : "{:04}{:02}{:02}".format(t.tm_year, t.tm_mon, t.tm_mday),
                't' : "{:02}:{:02}".format(t.tm_hour, t.tm_min),
    #            'n' : 1,            
                'v3' : round(cons_wh),
                'v4' : round(cons_w),
            }       
            if temperature is not None:
                payload['v8'] = temperature 

#    def add_status(self, pgrid_w, eday_kwh, temperature, voltage):
#        t = time.localtime()
#        payload = {
#            'd' : "{:04}{:02}{:02}".format(t.tm_year, t.tm_mon, t.tm_mday),
#            't' : "{:02}:{:02}".format(t.tm_hour, t.tm_min),
#            'v1' : round(eday_kwh * 1000),
#            'v2' : round(pgrid_w)
#        }
                       
#        print(payload) 
        self.call("https://pvoutput.org/service/r2/addstatus.jsp", payload)

    def add_day(self, data, temperatures):
        # Send day data in batches of 30.

        for chunk in [ data[i:i + 30] for i in range(0, len(data), 30) ]:

            readings = []
            for reading in chunk:
                dt = reading['dt']
                fields = [
                    dt.strftime('%Y%m%d'),
                    dt.strftime('%H:%M'),
                    str(round(reading['eday_kwh'] * 1000)),
                    str(reading['pgrid_w'])
                ]

                if temperatures is not None:
                    fields.append('')
                    fields.append('')
                    temperature = list(filter(lambda x: dt.timestamp() > x['time'], temperatures))[-1]
                    fields.append(str(temperature['temperature']))

                readings.append(",".join(fields))

            payload = {
                'data' : ";".join(readings)
            }

            self.call("https://pvoutput.org/service/r2/addbatchstatus.jsp", payload)

    def call(self, url, payload):
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
                        logging.warning("Only {} requests left, reset after {} seconds".format(
                            r.headers['X-Rate-Limit-Remaining'],
                            reset))
                if r.status_code == 403:
                    logging.warning("Forbidden: " + r.reason)
                    time.sleep(reset + 1)
                else:
                    r.raise_for_status()
                    break
            except requests.exceptions.RequestException as arg:
                logging.warning(r.text or str(arg))
            time.sleep(i ** 3)
        else:
            logging.error("Failed to call PVOutput API")


