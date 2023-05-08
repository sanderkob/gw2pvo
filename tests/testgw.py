import gw_api
import powerhandlerdate
from datetime import datetime
gw_station_id = '***REMOVED***'
gw_account = '***REMOVED***'
gw_password = '***REMOVED***'
gw = gw_api.GoodWeApi(gw_station_id, gw_account, gw_password)
data = gw.getCurrentReadings()
print(data)
# for inverterData in data['inverter']:
#     status = inverterData['status']
#     print(status)
last_refresh=data['last_refresh']
print (last_refresh)
# print (result['last_refresh'])
last_refresh = datetime.strptime(last_refresh, '%m/%d/%Y %H:%M:%S')
print (last_refresh)
print (last_refresh.timestamp())
last_refresh=int(last_refresh.timestamp())
print (last_refresh)
meter_data = powerhandlerdate.returndata(last_refresh)   
print (meter_data)