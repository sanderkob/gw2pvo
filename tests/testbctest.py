# # from datetime import datetime
# SMPresent = True
# try:
#    import powerhandler
# except ImportError:
#     SMPresent = False
#     logging.debug("No powerhandler present")
# print (SMPresent)    
# # date = datetime.now().timestamp()
# cons = powerhandler.returndata()  
# print (cons)
import smartmeterdict
meter_data = smartmeterdict.returndata()
print (meter_data)
print(type(meter_data))
print (meter_data["import_energy"])