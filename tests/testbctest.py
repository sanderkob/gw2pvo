# from datetime import datetime
SMPresent = True
try:
   import powerhandler
except ImportError:
    SMPresent = False
    logging.debug("No powerhandler present")
print (SMPresent)    
# date = datetime.now().timestamp()
cons = powerhandler.returndata()  
print (cons)
