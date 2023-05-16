# Parse any config file specification. We make this parser with add_help=False so
# that it doesn't accept -h, so no help is printed

from __init__ import __version__
import os
import sys
import argparse
from configparser import ConfigParser
import logging
from astral import LocationInfo
from astral.geocoder import lookup, database
from astral.location import Location

defaults: "dict[str:str]" = {
    'log': "info"
}
   
conf_parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,   #  formatter_class only relevant in commandline use, since add_help=False
    add_help=False
)
conf_parser.add_argument(
    "--config", help="Specify config file", metavar='FILE')
args, remaining_argv = conf_parser.parse_known_args()       #  remaining_argv not used

# Read configuration file and add it to the defaults hash.
if args.config:
    config = ConfigParser()
    config.read(args.config)
    if "Defaults" in config:
        defaults.update(dict(config.items("Defaults")))
    else:
        print ("Bad config file, missing Defaults section")
        exit
else:
    config = ConfigParser()
    config.read('gw2pvo.cfg')
#        print('Config',config)
    if "Defaults" in config:
        defaults.update(dict(config.items("Defaults")))
    else:
        print ("Bad config file, missing Defaults section")
        exit

# Parse rest of arguments
parser = argparse.ArgumentParser(
    description=__doc__,
    parents=[conf_parser],
)
parser.set_defaults(**defaults)                 # add options from the Defaults section to be parsed
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
parser.add_argument(
    "--pv-voltage", help="Send pv voltage instead of grid voltage", action='store_true')
parser.add_argument(
    "--skip-offline", help="Skip uploads when inverter is offline", action='store_true')
parser.add_argument(
    "--city", help="Sets timezone and skip uploads from dusk till dawn")
parser.add_argument(
    '--csv', help="Append readings to a Excel compatible CSV file, DATE in the name will be replaced by the current date")
parser.add_argument(
    '--mqtt', help="Enable MQTT subscribe (receive messages)", action='store_true')
parser.add_argument('--version', action='version',
                    version='%(prog)s ')
args = parser.parse_args()

# with action=store_true the args are True, even when set to no in  the config file
# so we check the actual value of the args
if isinstance(args.skip_offline, str):
    args.skip_offline = args.skip_offline.lower() in [
        'true', 'yes', 'on', '1']
if isinstance(args.pv_voltage, str):
    args.pv_voltage = args.pv_voltage.lower() in ['true', 'yes', 'on', '1']
if isinstance(args.mqtt, str):
    args.mqtt = args.mqtt.lower() in ['true', 'yes', 'on', '1']
if args.gw_station_id is None or args.gw_account is None or args.gw_password is None:
   print ("Missing --gw-station-id, --gw-account and/or --gw-password")
   exit

if args.skip_offline:
    print ("skip")
else:
    print("noskip")
if args.mqtt:
    print ("mqtt")
else:
    print("nomqtt")
print("mqtt: ", args.mqtt)
print("pv_voltage: ", args.pv_voltage)
print("skip_offline: ", args.skip_offline)
numeric_level = getattr(logging, args.log.upper(), None)
print("log level ",numeric_level)
print (args)
try:
    city = Location(lookup("Ede", database()))
except KeyError as ke:
    print('Key Not Found:', ke)
print ("verder")    
# logging.basicConfig(filename='/home/pi/gw2pvo.log',filemode='a',format='%(levelname)-8s %(message)s', level=numeric_level) # change to network log location
# logging.basicConfig(filename='gw2pvo.log',filemode='a',format='%(asctime)s %(levelname)-8s %(message)s',datefmt='%d-%m-%Y %H:%M:%S', level=numeric_level)
#test
logging.basicConfig(filename='gw2pvo.log',filemode='a', level=numeric_level)
logging.debug("gw2pvo version %s", __version__)
    
