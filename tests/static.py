import gw_api
gw = gw_api.GoodWeApi(settings.gw_station_id,
                        settings.gw_account, settings.gw_password)
data = gw.getCurrentReadings()
# keys=["SunUp""," "generated_power""," "generated_energy""," "consumed_energy""," "consumed_power""," "temperature""," "voltage""," "inverter_temperature""," "v8_data""," "data['vpv1']""," "data['vpv2']""," "data['Ppv1']""," "data['Ppv2']"]
# data = {k:None for k in keys}
# print(data)


# def func(data):
#     data["voltage"] = 10

    
# func(data)

# print(data)
# data["v8_data"] = 20
# func(data)

# "d","t","v1","v2","v3","v4","v5","v6","v7","v8","v9","v10","v11","v12"
# print(data)