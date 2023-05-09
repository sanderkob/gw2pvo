#!/usr/bin/python
"""Connects to Beeclear device ( https://forum.beeclear.nl/attachment.php?aid=35 )
       and downloads json, format https://www.beeclear.nl/docs/bc_api0.0.4.pdf    """

from urllib.parse import urlencode
from urllib.request import Request, urlopen
import base64
import json
import powerhandlerconfig                #stores host, username, password
from datetime import datetime
import time


class beeclear:
    """interaction with BeeClear, a web-based energy management system.
    Attributes:
        hostname : str
            The hostname or IP address of the BeeClear server.
        user : str
            The username to use for authentication.
        passwd : str
            The password to use for authentication.
        cookie : str or None
            A session cookie obtained after successful authentication. None if not connected.
    Methods:
        connect():
            Connect to the BeeClear server and authenticate the user with the provided credentials.
        send(command: str) -> bytes:
            Send a command to the BeeClear server and return the response data as bytes.
        getbeeclear(command: str) -> dict:
            Convenience method that connects to the BeeClear server, sends a command, and parses the response as JSON.
    Example:
        bc = beeclear('example.com', 'user', 'pass')
        bc.connect()
        data = bc.getbeeclear('get_data?duration=day&period=hour')
        print(data['values'])"""
        
        
    def __init__( self, hostname: str, user: str, passwd: str ):
        """initialize a new BeeClear client with the given credentials.
        Parameters:
            hostname : str
                The hostname or IP address of the BeeClear server.
            user : str
                The username to use for authentication.
            passwd : str
                The password to use for authentication."""
        self.hostname = hostname
        self.user = user
        self.passwd = passwd
        self.cookie = None


    def connect( self ):
        """connect to the BeeClear server and authenticate the user with the provided credentials.
        If successful, the session cookie is stored in self.cookie."""
        post_args = urlencode( { 'username': base64.b64encode((self.user).encode("utf-8")), 'password': base64.b64encode((self.passwd).encode("utf-8")) } )
        url = 'http://' + self.hostname + '/bc_login?' + post_args;
        req1 = Request(url)
        response = urlopen(req1)
        response_content = response.read()
        response_dict = json.loads(response_content.decode("utf-8"))
        if response_dict['status'] != 200:
            error_message = response_dict['message']
            raise Exception("Error {}: {}".format(response_dict['status'], error_message))
        self.cookie = response.headers.get('Set-Cookie')


    def send( self, command: str ) -> bytes:
        """send a command to the BeeClear server and return the response data as bytes.
        Parameters:
            command : str
                The command to send, in the format "command_name?param1=value1&param2=value2".
        Returns:
            bytes
                The raw response data, as bytes."""
        url = 'http://' + self.hostname + '/' + command
        req = Request(url)
        req.add_header('cookie', self.cookie)
        f = urlopen(req)
        data = f.read()
        f.close
        return data


    def getbeeclear(command) -> dict:
        """convenience method that connects to the BeeClear server, sends a command,
        and parses the response data as a JSON object.
        Parameters:
            command : str
                The command to send, in the format "command_name?param1=value1&param2=value2".
        Returns:
            dict
                The response data, parsed as a JSON object."""
        a = beeclear(powerhandlerconfig.host, powerhandlerconfig.username, powerhandlerconfig.password )
        a.connect()
        Str_beeclear = a.send(command)
        data = json.loads(Str_beeclear)
        local_time = datetime.now()
        return data

    
def returndata(date):
    """ returns a list of four values representing the current energy consumption and supply.
        The function first gets the energy consumption and supply data at midnight of the current date from the Beeclear API.
        It waits until the API returns non-empty data before proceeding. Then, it retrieves the current energy consumption and
        supply data from the API and calculates the energy consumed and supplied since midnight. The calculated values are
        returned as a list with the following elements:
        1. Energy imported in watt-hour (Wh) since midnight
        2. Energy imported in watt (W) currently
        3. Energy supplied in watt-hour (Wh) since midnight
        4. Energy supplied in watt (W) currently
    Returns:
        list:
            A list of four values representing the energy consumption and supply."""
    data0 = {}
    midnight = str(int(datetime.combine(datetime.now(),datetime.min.time()).timestamp()))  # calculate midnight date
    while not bool(data0.get(['meetwaarden'][0])):
        data0 = beeclear.getbeeclear('bc_getVal?type=elek&date='+midnight) # values at midnight
        #  print (data0.get(['meetwaarden'][0]))
        time.sleep(3)       # sometimes it takes some time to receive the data
    print(data0)
    print(date)
    # data = beeclear.getbeeclear('bc_getVal?type=elek&duration=60&period=2&date='+str(date))
    data = beeclear.getbeeclear('bc_getVal?type=elekw&duration=60') 
    # data = beeclear.getbeeclear('bc_current?type=elek&date='+str(date))

    ImportEnergy0 = data0['meetwaarden'][0]['val'][0]['verbl'] + data0['meetwaarden'][0]['val'][0]['verb']
    ExportEnergy0 = data0['meetwaarden'][0]['val'][0]['levl'] + data0['meetwaarden'][0]['val'][0]['lev']
    print(data)
    ImportEnergy = data['meetwaarden'][0]['val'][0]['verbl'] + data['meetwaarden'][0]['val'][0]['verb']
    ExportEnergy = data['meetwaarden'][0]['val'][0]['levl'] + data['meetwaarden'][0]['val'][0]['lev']
    ImportPower = data['meetwaarden'][0]['val'][0]['v'] + data['meetwaarden'][0]['val'][0]['vl']
    ExportPower = data['meetwaarden'][0]['val'][0]['l'] + data['meetwaarden'][0]['val'][0]['ll']
    # ImportEnergy = data['meetwaarden'][0]['val'][0]['ImportEnergy']
    # ExportEnergy = data['meetwaarden'][0]['val'][0]['ExportEnergy']
    # ul=data['meetwaarden'][0]['val'][0]['verbl']
    # uh=data['meetwaarden'][0]['val'][0]['verb']
    # gl=data['meetwaarden'][0]['val'][0]['levl']
    # gh=data['meetwaarden'][0]['val'][0]['lev']

    # ul=data['ul']
    # uh=data['uh']
    # u=data['u']
    # gl=data['gl']
    # gh=data['gh']
    # g=data['g']

    # cons_wh = (uh-uh0) + (ul-ul0)
    # cons_w = u
    # sup_wh = (gl-gl0) + (gh-gh0)
    # sup_w = g
    ImportEnergy = ImportEnergy - ImportEnergy0
    ExportEnergy = ExportEnergy - ExportEnergy0
    
    # sup_wh = (gl-gl0) + (gh-gh0)
    # sup_w = g
    result = [ImportEnergy, ImportPower, ExportEnergy, ExportPower]
    # cons = [cons_wh, cons_w, sup_wh, sup_w]
    print (result)
    return result