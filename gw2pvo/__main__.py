#!/usr/bin/env python3

from __init__ import __version__
import os
import sys
if sys.version_info < (3, 6):
    sys.exit('Sorry, you need at least Python 3.6 for Astral 2')
import logging
import traceback   # added in version 2"
import argparse
import locale
import time
from datetime import datetime
from configparser import ConfigParser
from astral.geocoder import lookup, database
from astral.location import Location
import paho.mqtt.client as mqtt
import uuid
import gw_api
import gw_csv
import pvo_api
# import smartmeter if present, otherwise set smartmeter_present false
smartmeter_present = True
try:
    import smartmeter_mqtt
except ImportError:
    smartmeter_present = False
    logging.debug("No smart meter present")

__author__ = "Mark Ruys, Sander Kobussen"
__copyright__ = "Copyright 2017-2020, Mark Ruys; 2023 Sander Kobussen"
__license__ = "MIT"
__email__ = "mark@paracas.nl"
__doc__ = "Upload GoodWe power inverter data to PVOutput.org"

# defaults

# # initializing global variables
v8_data = None  # user variable may be supplied by MQTT

# the following variables are in global scope to make their values persistent between function calls of run_once()
# For 24h registration of power consumption, the supplied energy from smartmeter is needed when the inverter is offline

keys = ["d", "t", "v1", "v2", "v3", "v4", "v5", "v6",
        "v7", "v8", "v9", "v10", "v11", "v12"]  # fill pvo_data
pvo_data = {k: None for k in keys}
data = {}
last_consumed_power = 120     # if consumed_power is negative, replace by earlier value
last_consumed_energy = 0      # if consumed energy decreases, replace by earlier value
mqtt_broker = ""
mqtt_topic = ""
telegram = ""
telegram_midnight = ""


def on_message(client, userdata, message) -> None:
    """MQTT callback funtion for incoming message
    Args:
        client (paho.mqtt.client.Client): client instance that is calling the callback
        userdata (_type_): user data of any type, can be set when creating a new client - not used
        message (str): _description_    """
    global v8_data
    global telegram
    message.payload = message.payload.decode("utf-8")
    # print("message received ", message.payload)
    # print("message topic=", message.topic)
    # print("message qos=", message.qos)
    # print("message retain flag=", message.retain)
    if message.topic == mqtt_topic:
        # split in case message contains severable items separated by spaces
        msglist = message.payload.split(" ")
        logging.info("msglist: %s", msglist)
        # first or only item in message
        v8_data = msglist[0]
    if message.topic == 'beeclear':
        telegram = message.payload


def on_connect(client, userdata, flags, rc) -> None:
    """MQTT called when connection established
    Args:
        client (paho.mqtt.client.Client): client instance that is calling the callback
        userdata (_type_): user data of any type, can be set when creating a new client - not used
        flags (dict): flags contains response flags from the broker:
            flags['session present'] -  this flag is only useful for a client that uses clean session=0.
                                        If such clients reconnect to a broker it has previously connected to,
                                        this flag indicates whether the broker still has the
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
        logging.info("connected OK Returned code=0")
        # subscribe to topic with qos=1
        client.subscribe(mqtt_topic, 1)
    else:
        logging.error("Bad connection Returned code= %d", rc)


def on_disconnect(client, userdata, rc) -> None:
    """MQTT called when the client disconnects from the broker.
    Args:
        client (paho.mqtt.client.Client): client instance that is calling the callback
        userdata (_type_): user data of any type, can be set when creating a new client - not used
        rc (int): rc indicates the disconnection state. If 0 (MQTT_ERR_SUCCESS),
                  the callback was called in response to a disconnect() call.
                  If any other value, the disconnection was unexpected (e.g. network error)"""
    logging.warning("Client Got Disconnected")
    if rc != 0:
        logging.warning('Unexpected MQTT disconnection. Will auto-reconnect')
    else:
        logging.warning(f'rc value: {rc}')
    try:
        client.connect(mqtt_broker, keepalive=60)
    except Exception as e:
        logging.error(f'Error in Retrying to Connect: {e}')


def on_log(client, userdata, level, buf) -> None:
    """called when the client has log information.
    Args:
        client (paho.mqtt.client.Client): client instance that is calling the callback
        userdata (_type_): user data of any type, can be set when creating a new client - not used
        level (str):  Level is one of MQTT_LOG_INFO, MQTT_LOG_NOTICE, MQTT_LOG_WARNING, MQTT_LOG_ERR or MQTT_LOG_DEBUG
        buf (_type_): log message"""
    logging.debug(f"log: {buf}")


def run_once(pvo_data, data, settings, city) -> None:
    """misleading name, the function is executed every 'Interval' minutes.
    It handles downloads of data from powerhandler, uploads to PVOutput, copying of day readings and preparing csv file.
    Args:
        settings (_type_): config settings from file, passed from args
        city (dict): city geo-location derived from city name in config, used to set timezone in non-Windows and skip uploads from dusk till dawn"""
    global last_consumed_power
    global last_consumed_energy
    global v8_data
    global telegram
    global telegram_midnight

    # inline function to round if not None
    def r(x): return round(x) if x else None

    # print (telegram)
    
    # Check daylight for enabling pvo upload
    sun_up = True
    if city:
        now = datetime.time(datetime.now())
        if now < city.dawn().time() or now > city.dusk().time():
            sun_up = False
            logging.debug("It is night, do not upload PV data")

    # Only fetch data when sup up or when no data stored yet
    if sun_up or not bool(data):             #
        gw = gw_api.GoodWeApi(settings.gw_station_id,
                              settings.gw_account, settings.gw_password)
        data = gw.getCurrentReadings()
    # Request smart meter reading
    
    # Check if we want to abort when offline.
    # Note that this also disables upload of consumption data and outside temperature
    if settings.skip_offline:
        if data['status'] == 'Offline':
            logging.debug("Skipped upload as the inverter is offline")
            return

    # Append reading to named CSV file, consisting of: status / current power (w) / produced today (kWh) / produced total (kWh)
    if settings.csv:
        if data['status'] == 'Offline':
            logging.debug("Don't append offline data to CSV file")
        else:
            locale.setlocale(locale.LC_ALL, locale.getlocale())
            csv = gw_csv.GoodWeCSV(settings.csv)
            csv.append(data)

    # no temperature upload, the outside temperature can be derived from OpenWeatherMap through automatic upload in PVOutput to v5
    temperature = None
    inverter_temperature = data['temperature']
    voltage = data['grid_voltage']
    if settings.pv_voltage:
        voltage = data['pv_voltage']
    generated_energy = int(1000 * data['eday_kwh'])
    logging.debug(
        f"generated energy = {generated_energy}, data['eday_kwh'] = {data['eday_kwh']}")
    generated_power = round(data['pgrid_w'])

    # is there a smart meter available to upload consumption data?
    if smartmeter_present and len(telegram):
        print(telegram)
        print(len(telegram))
        if len(telegram):
            print('true')
        else:
            print('false')
        meter_data = smartmeter_mqtt.returndata(telegram, telegram_midnight)  # fetch power meter readings
        # logging.debug(
        #     f'import_energy {meter_data[0]}, import_power {meter_data[1]}, export_energy {meter_data[2]}, export_power {meter_data[3]}')
        logging.debug(
            f'import_energy {meter_data["import_energy"]}, import_power {meter_data["import_power"]}, export_energy {meter_data["export_energy"]}, export_power {meter_data["export_power"]}')
        # consumed energy = imported energy - exported energy + generated energy
        consumed_energy = round(
            meter_data["import_energy"] - meter_data["export_energy"] + generated_energy)

        # at the start of the day, reset last_cons_wh and eday_wh
        # midnight with 5 minutes (301 sec) margin, that is the run_once interval
        if (datetime.now().timestamp() - datetime.combine(datetime.now(), 
                                                          datetime.min.time()).timestamp() < 301): 
            telegram_midnight=telegram
            print (telegram_)
            # should be 0 until we receive new data, so make it persistent between function calls
            data['eday_kwh'] = 0
            consumed_energy = round(meter_data["import_energy"] - meter_data["export_energy"])
            last_consumed_energy = consumed_energy

        if consumed_energy < last_consumed_energy:   # consumed energy can not become less
            consumed_energy = last_consumed_energy
            last_consumed_energy = consumed_energy

        # consumed power  cons_w  = imported power - exported power + produced power
        consumed_power = round(meter_data["import_power"] - meter_data["export_power"] + generated_power)
        if consumed_power < 0:               # power cannot be negative
            consumed_power = last_consumed_power
            last_consumed_power = consumed_power

        logging.debug(
            f'Consumption on {datetime.now()}:19 : {consumed_energy}Wh, {consumed_power}W, Production {generated_energy}Wh, {generated_power}W, v8data {v8_data}')

    pvo_data = {
        'v6': voltage,
        'v7': inverter_temperature,
        'v8': v8_data
    }

    if smartmeter_present:
        update = {
            'v3': consumed_energy,
            'v4': consumed_power
        }
        pvo_data.update(update)
    elif sun_up:
        update = {
            'v1': generated_energy,
            'v2': generated_power
        }
        pvo_data.update(update)
    if sun_up:
        update = {
            'v1': generated_energy,
            'v2': generated_power,
            'v9': r(data['vpv1']),
            'v10': r(data['vpv2']),
            'v11': r(data['Ppv1']),
            'v12': r(data['Ppv2'])
        }
        pvo_data.update(update)
    logging.debug(
        f"check generated {generated_power} = {data['Ppv1']} + {data['Ppv2']}")
    # test
    # if settings.pvo_system_id and settings.pvo_api_key:
    #     pvo = pvo_api.PVOutputApi(settings.pvo_system_id, settings.pvo_api_key)
    #     pvo.add_status(pvo_data)
    # else:
    #     logging.debug(str(data))
    #     logging.warning("Missing PVO id and/or key")


def copy(settings) -> None:
    """copy day of readings from GoodWe to PVOutput. Interval will be 10 minutes.
       Beware that the date parameter must be not be older than 14 days from the current date,
       in donation mode, not more than 90 days.
    Args:
        settings (Namespace): the settings from the gw2pvo.cfg file"""
    # Fetch readings from GoodWe
    date = datetime.strptime(settings.date, "%Y-%m-%d")
    gw = gw_api.GoodWeApi(settings.gw_station_id,
                          settings.gw_account, settings.gw_password)
    daydata = gw.getDayReadings(date)

    if settings.pvo_system_id and settings.pvo_api_key:
        # Submit readings to PVOutput
        pvo = pvo_api.PVOutputApi(settings.pvo_system_id, settings.pvo_api_key)
        pvo.add_day(daydata['entries'])
    else:
        for entry in daydata['entries']:
            logging.info(
                f"{entry['dt']}: {entry['pgrid_w']:6.0f} W {entry['eday_wh']:6.2f} kWh")
        logging.warning("Missing PVO id and/or key")


def run() -> None:
    """main function:
       parses gw2pvo.cfg configuration file
       configures logging,
       configures mqtt (if enabled),
       triggers run_once and repeats that at intervals"""
    global mqtt_topic
    global mqtt_broker
    defaults: dict[str, str] = {
        'log': "info"
    }

    # Parse any config file specification.
    # add_help=False so that it doesn't accept -h as input and no help is printed
    conf_parser = argparse.ArgumentParser(
        # formatter_class only relevant in commandline use, since add_help=False, not tested
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False
    )
    conf_parser.add_argument(
        "--config", help="Specify config file", metavar='FILE')
    args, remaining_argv = conf_parser.parse_known_args()  # remaining_argv not used

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
        config.read('gw2pvo/gw2pvo.cfg')  # test
        # config.read('gw2pvo.cfg')
        if "Defaults" in config:
            defaults.update(dict(config.items("Defaults")))
        else:
            sys.exit("Bad config file, missing Defaults section")

    # Parse rest of arguments
    parser = argparse.ArgumentParser(
        description=__doc__,
        parents=[conf_parser],
    )
    # add options from the Defaults section to be parsed
    parser.set_defaults(**defaults)
    parser.add_argument(
        "--gw-station-id", help="GoodWe station ID", metavar='ID')
    parser.add_argument(
        "--gw-account", help="GoodWe account", metavar='ACCOUNT')
    parser.add_argument(
        "--gw-password", help="GoodWe password", metavar='PASSWORD')
    parser.add_argument(
        "--pvo-system-id", help="PVOutput system ID", metavar='ID')
    parser.add_argument(
        "--pvo-api-key", help="PVOutput API key", metavar='KEY')
    parser.add_argument(
        "--pvo-interval", help="PVOutput interval in minutes", type=int, choices=[5, 10, 15])
    parser.add_argument(
        "--log", help="Set log level (default info)", choices=['debug', 'info', 'warning', 'critical'])
    parser.add_argument(
        "--date", help="Copy all readings (max 14/90 days ago)", metavar='YYYY-MM-DD')
    parser.add_argument(
        "--pv-voltage", help="Send pv voltage instead of grid voltage", action='store_true')
    parser.add_argument(
        "--skip-offline", help="Skip uploads when inverter is offline", action='store_true')
    parser.add_argument(
        "--city", help="Sets timezone and skip uploads from dusk till dawn")
    parser.add_argument(
        '--csv', help="Append readings to a Excel CSV file, DATE in the name will be replaced by the current date")
    parser.add_argument(
        '--mqtt', help="Enable MQTT subscribe (receive messages)", type=str, nargs=2)
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)
    args = parser.parse_args()

    # enable mqtt if mqtt_broker and mqtt_topic are configured
    mqtt_present = False
    mqtt_args = args.mqtt.split()
    if len(mqtt_args) == 2:
        mqtt_broker = mqtt_args[0]
        mqtt_topic = mqtt_args[1]
        mqtt_present = True

    # added in version2
    # with action=store_true the args are True, even when set to 'no' in  the config file
    # so we check the actual value of the args
    if isinstance(args.skip_offline, str):
        args.skip_offline = args.skip_offline.lower() in [
            'true', 'yes', 'on', '1']
    if isinstance(args.pv_voltage, str):
        args.pv_voltage = args.pv_voltage.lower() in ['true', 'yes', 'on', '1']

    if args.gw_station_id is None or args.gw_account is None or args.gw_password is None:
        sys.exit("Missing --gw-station-id, --gw-account and/or --gw-password")
    if args.city:
        try:
            city = Location(lookup(args.city, database()))
        except KeyError as ke:
            sys.exit(f"City not found - {ke}")
    # this is disabled, maybe necessary when running in windows:
    #   os.environ['TZ'] = city.timezone
    #   time.tzset()
    else:
        city = None

    # Configure the logging
    # numeric level:
    #     NOTSET=0
    #     DEBUG=10
    #     INFO=20
    #     WARN=30
    #     ERROR=40
    #     CRITICAL=50
    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {numeric_level}')

    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%d-%m-%Y %H:%M:%S',
        level=numeric_level)

    logging.debug("gw2pvo version %s", __version__)

    # logging configured, start logging what we still had to log from before:
    logging.debug(args)
    logging.debug(f"Timezone {datetime.now().astimezone().tzinfo}")

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
    if mqtt_present:
        # create new instance with unique ID
        client = mqtt.Client("gw2pvo" + str(uuid.uuid4()))
        client.connect(mqtt_broker, keepalive=60)           # connect to broker
        client.on_message = on_message
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        # client.on_log=on_log                              # for troubleshooting
        client.loop_start()                                 # start the loop
        client.subscribe(mqtt_topic, 1)
        client.subscribe('beeclear', 1)

    startTime = datetime.now()
    print(startTime)

    while True:
        try:
            run_once(pvo_data, data, args, city)
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
