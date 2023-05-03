#!/usr/bin/env python3
"""added extra debug logging, no averaging    """

import sys
import os
if sys.version_info < (3, 6):
    sys.exit('Sorry, you need at least Python 3.6 for Astral 2')
import logging
import traceback                        # added error traceback in V2"
import argparse
import locale
import time
from datetime import datetime
from configparser import ConfigParser
from astral import LocationInfo
from astral.geocoder import lookup, database
from astral.location import Location
import paho.mqtt.client as mqtt         # added MQTT, currently not in use in V2
import gw_api
import gw_csv
import pvo_api
from __init__ import __version__
import bcstartv3
"""added import power meter readings from Beeclear in V2
        Beeclear is a device that makes P1 information available on the LAN"""

__author__ = "Mark Ruys, Sander Kobussen"
__copyright__ = "Copyright 2017-2020, Mark Ruys; 2023 Sander Kobussen"
__license__ = "MIT"
__email__ = "mark@paracas.nl"
__doc__ = "Upload GoodWe power inverter data to PVOutput.org"

# defaults
MQTT_SERVER = "192.168.1.236"
MQTT_TOPIC =  "received_data"  
data = {}   # data in global scope to make persistent between function calls of run_once
received_data - None              # dummy user variable to publish with MQTT,

# initializing global variable
last_eday_kwh = 0
last_cons_w = 120           # if cons_w (verbruik, watt) is negative, replace by earlier value
last_cons_wh = 0            # if cons_wh decreases, replace by earlier value


def on_message(client, userdata, message) -> None:
    """MQTT callback funtion for incoming message
    Args:
        client (paho.mqtt.client.Client): client instance that is calling the callback
        userdata (_type_): user data of any type, can be set when creating a new client - not used
        message (str): _description_    """
    message.payload = message.payload.decode("utf-8")
    print("message received ", received_data)
    print("message topic=", message.topic)
    print("message qos=", message.qos)
    print("message retain flag=", message.retain)
    #    msglist = message.payload.split(" ")       # in case message contains severable ietems separated by spaces
    #    print(msglist)
    received_data = msglist[0]                     # first or only item in message


def on_connect(client, userdata, flags, rc) -> None:
    """MQTT called when connection established
    Args:
        client (paho.mqtt.client.Client): client instance that is calling the callback
        userdata (_type_): user data of any type, can be set when creating a new client - not used
        flags (dict): flags contains response flags from the broker:
            flags['session present'] -  this flag is useful for clients that are
                                        using clean session set to 0 only. If a client with clean
                                        session=0, that reconnects to a broker that it has previously
                                        connected to, this flag indicates whether the broker still has the
                                        session information for the client. If 1, the session still exists.
            rc (int): Connection Return Codes
                                        0: Connection successful
                                        1: Connection refused - incorrect protocol version
                                        2: Connection refused - invalid client identifier
                                        3: Connection refused - server unavailable
                                        4: Connection refused - bad username or password
                                        5: Connection refused - not authorised
                                        6-255: Currently unused."""
    if rc == 0:
        logging.warning("connected OK Returned code=0")
        logging.warning(client)
        client.subscribe(MQTT_TOPIC, 1)              # qos=1
    else:
        logging.error("Bad connection Returned code=", rc)


def on_disconnect(client, userdata, rc) -> None:
    """MQTT called when the client disconnects from the broker.
    Args:
        client (paho.mqtt.client.Client): client instance that is calling the callback
        userdata (_type_): user data of any type, can be set when creating a new client - not used
        rc (int): rc indicates the disconnection state. If 0 (MQTT_ERR_SUCCESS),
                  the callback was called in response to a disconnect() call. 
                  If any other value the disconnection was unexpected (e.g. network error)"""    
    logging.warning("Client Got Disconnected")
    if rc != 0:
        logging.warning('Unexpected MQTT disconnection. Will auto-reconnect')
    else:
        logging.warning('rc value:' + str(rc))
    try:
        client.connect(MQTT_SERVER, keepalive=60)
    except:
        logging.error('Error in Retrying to Connect')


def on_log(client, userdata, level, buf) -> None:
    """called when the client has log information.
    Args:
        client (paho.mqtt.client.Client): client instance that is calling the callback
        userdata (_type_): user data of any type, can be set when creating a new client - not used
        level (str):  Level is one of MQTT_LOG_INFO, MQTT_LOG_NOTICE, MQTT_LOG_WARNING, MQTT_LOG_ERR or MQTT_LOG_DEBUG
        buf (_type_): log message"""    
    logging.debug("log: ", buf)


def run_once(settings, city) -> None:
    """executed every 'Interval' minutes
    Args:
        settings (_type_): config settings from file, passed from args
        city (dict): city geo-location derieved from city name in config, to set timezone in non-Windows and skip uploads from dusk till dawn    """    
    global last_cons_w
    global last_cons_wh
    global received_data
    global data

    # Check daylight for shaping pvo upload
    SunUp = True
    if city:
        now = datetime.time(datetime.now())
        # print(now,city.dawn().time(),city.dusk().time())
        if now < city.dawn().time() or now > city.dusk().time():
            SunUp = False
            logging.debug("Modified upload as it's night")

    # Only fetch data when sup up or when no data stored yet
    if SunUp or not bool(data):             # 
        gw = gw_api.GoodWeApi(settings.gw_station_id,
                              settings.gw_account, settings.gw_password)
        data = gw.getCurrentReadings()
        # print (data)

    # Check if we want to abort when offline. Note that this also disables upload of consumption data and outside temperature
    if settings.skip_offline:
        if data['status'] == 'Offline':
            logging.debug("Skipped upload as the inverter is offline")
            return

    # Append reading to CSV file
    if settings.csv:
        if data['status'] == 'Offline':
            logging.debug("Don't append offline data to CSV file")
        else:
            locale.setlocale(locale.LC_ALL, locale.getlocale())
            csv = gw_csv.GoodWeCSV(settings.csv)
            csv.append(data)

    # Submit reading to PVOutput, if they differ from the previous data
    eday_kwh = data['eday_kwh']
    if data['pgrid_w'] == 0 and abs(eday_kwh - last_eday_kwh) < 0.001:
        logging.debug("Ignore unchanged reading")
    else:
        last_eday_kwh = eday_kwh

    # no temperature upload, outside temperature is derived from OpenWeatherMap through automatic upload in pvoutput
    temperature = None

    voltage = data['grid_voltage']
    if settings.pv_voltage:
        voltage = data['pv_voltage']
    eday_wh = int(1000 * data['eday_kwh'])
    # print ("eday_wh, data['eday_kwh'] ", eday_wh, data['eday_kwh'])
    logging.debug("eday_wh = %s , data['eday_kwh'] = %s ", eday_wh, data['eday_kwh'])
    pgrid_w = data['pgrid_w']
    cons = bcstartv3.returndata()           # fetch power meter readings
    
    # calculate net consumption as difference of goodwe data and power meter data
    # consumed energy cons_wh = imported energy - exported energy + produced energy
    # consumed power  cons_w  = imported power - exported power + produced power
    # produced energy prod_wh = eday_wh from gw
    # produced power  prop_w  = pgrid_w from gw
    
    cons_wh = cons[0] - cons[2] + eday_wh       # consumed energy cons_wh = imported energy - exported energy + produced energy
    logging.debug("cons_wh = %s ", cons_wh)
    
    # at start of the day, reset last_cons_wh and eday_wh
    if (datetime.now().timestamp() - datetime.combine(datetime.now(), datetime.min.time()).timestamp() < 301):    # at midnight
        data['eday_kwh'] = 0
        cons_wh = cons[0] - cons[2]
        last_cons_wh = cons_wh

    if cons_wh < last_cons_wh:   # consumed energy can not become less
        cons_wh = last_cons_wh
    last_cons_wh = cons_wh

    cons_w = cons[1] - cons[3] + pgrid_w    # consumed power  cons_w  = imported power - exported power + produced power
    if cons_w < 0:               # power cannot be negative
        cons_w = last_cons_w
    last_cons_w = cons_w

    prod_wh = eday_wh    # produced energy prod_wh = eday_wh from gw
    prod_w = pgrid_w    # produced power  prop_w  = pgrid_w from gw
    # print ('prod_wh, prod_w, cons_wh, cons_w ',prod_wh, prod_w, cons_wh, cons_w)
    logging.debug('prod_wh = %s, prod_w = %s, cons_wh =%s, cons_w =%s',
                  prod_wh, prod_w, cons_wh, cons_w)

    #  extra: upload of received_data (from MQTT), goes to v7
    if settings.pvo_system_id and settings.pvo_api_key:
        pvo = pvo_api.PVOutputApi(settings.pvo_system_id, settings.pvo_api_key)
        pvo.add_status(SunUp, prod_w, prod_wh, cons_wh, cons_w, temperature, voltage,
                       data['temperature'], received_data, data['vpv1'], data['vpv2'], data['Ppv1'], data['Ppv2'])
    else:
        logging.debug(str(data))
        logging.warning("Missing PVO id and/or key")

    logging.debug('Consumption on %.19s : %s Wh, %s W, Production %s Wh, %s W, temp %s, Vcc %s, FW %s\n',
                  datetime.now(), cons_wh, cons_w, prod_wh, prod_w, received_data)



def copy(settings) -> None:
    # Fetch readings from GoodWe
    date = datetime.strptime(settings.date, "%Y-%m-%d")

    gw = gw_api.GoodWeApi(settings.gw_station_id,
                          settings.gw_account, settings.gw_password)
    data = gw.getDayReadings(date)

    if settings.pvo_system_id and settings.pvo_api_key:
        # Submit readings to PVOutput
        pvo = pvo_api.PVOutputApi(settings.pvo_system_id, settings.pvo_api_key)
        pvo.add_day(data['entries'])
    else:
        for entry in data['entries']:
            logging.info("{}: {:6.0f} W {:6.2f} kWh".format(
                entry['dt'],
                entry['pgrid_w'],
                entry['eday_wh'],
            ))
        logging.warning("Missing PVO id and/or key")


def run() -> None:
    defaults: dict[str, str] = {
        'log': "info"
    }

    # Parse any config file specification. We make this parser with add_help=False so
    # that it doesn't parse -h and print help.
    conf_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False
    )
    conf_parser.add_argument(
        "--config", help="Specify config file", metavar='FILE')
    args, remaining_argv = conf_parser.parse_known_args()

    # Read configuration file and add it to the defaults hash.
    if args.config:
        config = ConfigParser()
        config.read(args.config)
        if "Defaults" in config:
            defaults.update(dict(config.items("Defaults")))
        else:
            sys.exit("Bad config file, missing Defaults section")
    else:
        config = ConfigParser()
        config.read('gw2pvo.cfg')
#        print('Config',config)
        if "Defaults" in config:
            defaults.update(dict(config.items("Defaults")))
        else:
            sys.exit("Bad config file, missing Defaults section")

    # Parse rest of arguments
    parser = argparse.ArgumentParser(
        description=__doc__,
        parents=[conf_parser],
    )
    parser.set_defaults(**defaults)
    parser.add_argument("--gw-station-id",
                        help="GoodWe station ID", metavar='ID')
    parser.add_argument(
        "--gw-account", help="GoodWe account", metavar='ACCOUNT')
    parser.add_argument(
        "--gw-password", help="GoodWe password", metavar='PASSWORD')
    parser.add_argument("--pvo-system-id",
                        help="PVOutput system ID", metavar='ID')
    parser.add_argument(
        "--pvo-api-key", help="PVOutput API key", metavar='KEY')
    parser.add_argument(
        "--pvo-interval", help="PVOutput interval in minutes", type=int, choices=[5, 10, 15])
    parser.add_argument("--log", help="Set log level (default info)",
                        choices=['debug', 'info', 'warning', 'critical'])
    parser.add_argument(
        "--date", help="Copy all readings (max 14/90 days ago)", metavar='YYYY-MM-DD')
    parser.add_argument("--pv-voltage", help="Send pv voltage instead of grid voltage", action='store_true')
    parser.add_argument(
        "--skip-offline", help="Skip uploads when inverter is offline", action='store_true')
    parser.add_argument(
        "--city", help="Sets timezone and skip uploads from dusk till dawn")
    parser.add_argument(
        '--csv', help="Append readings to a Excel compatible CSV file, DATE in the name will be replaced by the current date")
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)
    args = parser.parse_args()

    # Configure the logging
    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    # logging.basicConfig(filename='/home/pi/gw2pvo.log',filemode='a',format='%(levelname)-8s %(message)s', level=numeric_level) # change to network log loaction
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%d-%m-%Y %H:%M:%S', level=numeric_level)
    logging.debug("gw2pvo version " + __version__)

    if isinstance(args.skip_offline, str):
        args.skip_offline = args.skip_offline.lower() in [
            'true', 'yes', 'on', '1']
    if isinstance(args.pv_voltage, str):
        args.pv_voltage = args.pv_voltage.lower() in ['true', 'yes', 'on', '1']
    logging.debug(args)

    if args.gw_station_id is None or args.gw_account is None or args.gw_password is None:
        sys.exit("Missing --gw-station-id, --gw-account and/or --gw-password")

    if args.city:
        city = Location(lookup(args.city, database()))
        # disabled, maybe necessary when running in windows
        # os.environ['TZ'] = city.timezone
        # time.tzset() 
    else:
        city = None
    logging.debug("Timezone {}".format(datetime.now().astimezone().tzinfo))

    # Check if we want to copy old data
    if args.date:
        try:
            copy(args)
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as exp:
            logging.error(exp)
        sys.exit()

    # setup MQTT
    client = mqtt.Client("gw2pvo")  # create new instance
    client.connect(MQTT_SERVER, keepalive=60)  # connect to broker
    client.on_message = on_message
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    # client.on_log=on_log
    client.loop_start()  # start the loop
    client.subscribe(MQTT_TOPIC, 1)  # topic received_data, qos=1

    startTime = datetime.now()
    print(startTime)

    while True:
        try:
            run_once(args, city)
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as exp:
            print(datetime.now(), traceback.format_exc())
            logging.error(exp)
        if args.pvo_interval is None:
            break
        interval = args.pvo_interval * 60
        time.sleep(interval - (datetime.now() - startTime).seconds % interval)


if __name__ == "__main__":
    run()