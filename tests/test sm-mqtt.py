import re

# telegram = "/XMX5LGBBFG1009343400\n\n1-3:0.2.8(42)\n0-0:1.0.0(230508194533S)\n0-0:96.1.1(4530303331303033323233343730313136)\n1-0:1.8.1(013820.044*kWh)\n1-0:1.8.2(011954.981*kWh)\n1-0:2.8.1(001957.999*kWh)\n1-0:2.8.2(004472.483*kWh)\n0-0:96.14.0(0002)\n1-0:1.7.0(00.418*kW)\n1-0:2.7.0(00.000*kW)\n0-0:96.7.21(00004)\n0-0:96.7.9(00002)\n1-0:99.97.0(2)(0-0:96.7.19)(210127112334W)(0000010077*s)(200928120257S)(0000000239*s)\n1-0:32.32.0(00000)\n1-0:32.36.0(00000)\n0-0:96.13.1()\n0-0:96.13.0()\n1-0:31.7.0(003*A)\n1-0:21.7.0(00.418*kW)\n1-0:22.7.0(00.000*kW)\n0-1:24.1.0(003)\n0-1:96.1.0(4730303235303033323736393236303135)\n0-1:24.2.1(230508190000S)(07733.832*m3)\n!A92D"


def decode_mqtt(telegram):
# Extracting the values using regular expressions
    date = re.search(r"0-0:1\.0\.0\((.*?)S\)", telegram).group(1)
    meter_reading_import_low_tariff = float(re.search(r"1-0:1\.8\.1\((.*?)\*kWh\)", telegram).group(1))
    meter_reading_import_high_tariff = float(re.search(r"1-0:1\.8\.2\((.*?)\*kWh\)", telegram).group(1))
    meter_reading_export_low_tariff = float(re.search(r"1-0:2\.8\.1\((.*?)\*kWh\)", telegram).group(1))
    meter_reading_export_high_tariff = float(re.search(r"1-0:2\.8\.2\((.*?)\*kWh\)", telegram).group(1))
    import_power = float(re.search(r"1-0:1\.7\.0\((.*?)\*kW\)", telegram).group(1))
    export_power = float(re.search(r"1-0:2\.7\.0\((.*?)\*kW\)", telegram).group(1))

    # # Printing the extracted values
    # print("Date:", date)
    # print("Meter Reading Import Low Tariff:", meter_reading_import_low_tariff)
    # print("Meter Reading Import High Tariff:", meter_reading_import_high_tariff)
    # print("Meter Reading Export Low Tariff:", meter_reading_export_low_tariff)
    # print("Meter Reading Export High Tariff:", meter_reading_import_high_tariff)
    # print("Import power", import_power)
    # print("Export power", export_power)

    meter_data = {"Date:" : date, 
                "Meter Reading Import Low Tariff:" :  meter_reading_import_low_tariff, 
                "Meter Reading Import High Tariff:" : meter_reading_import_high_tariff, 
                "Meter Reading Export Low Tariff:" :  meter_reading_export_low_tariff,
                "Import power" : import_power,
                "Export power" :  export_power
    }

    # print("Meter Reading Export High Tariff:", meter_reading_import_high_tariff)
    # print("Import power", import_power)
    # print("Export power", export_power)
    return meter_data

def returndata(telegram, telegram_midnight):
    meter = decode_mqtt(telegram)
    meter_midnight = decode_mqtt(telegram_midnight)
    
    import_energy = (uh-uh0) + (ul-ul0)
    import_energy = (meter[meter_reading_import_high_tariff] - 
                     meter_midnight[meter_reading_import_high_tariff] +
                     meter[meter_reading_import_low_tariff] - 
                     meter_midnight[meter_reading_import_low_tariff]
    )         
    import_power = meter['import_power']
    export_energy = (meter[meter_reading_export_high_tariff] - 
                    meter_midnight[meter_reading_export_high_tariff] +
                    meter[meter_reading_export_low_tariff] - 
                    meter_midnight[meter_reading_export_low_tariff]
    )   
    export_power = meter['export_power']

    # meter_data = [import_energy, import_power, export_energy, export_power]
    meter_data = {"import_energy" : import_energy, "import_power" : import_power, "export_energy" : export_energy, "export_power" : export_power}

    return meter_data