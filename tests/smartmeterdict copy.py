#!/usr/bin/python
"""Connects to Beeclear device ( https://forum.beeclear.nl/attachment.php?aid=35 )
       and downloads json, format https://www.beeclear.nl/docs/bc_api0.0.4.pdf    """

from urllib.parse import urlencode
from urllib.request import Request, urlopen
import base64
import json
import smartmeterconfig  # stores host, username, password
from datetime import datetime
import time
import http.client


class beeclear:
    """interaction with BeeClear smart meter app
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

    def __init__(self, hostname: str, user: str, passwd: str):
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

    def connect(self):
        """connect to the BeeClear server and authenticate the user with the provided credentials.
        If successful, the session cookie is stored in self.cookie."""
        post_args = urlencode({'username': base64.b64encode((self.user).encode(
            "utf-8")), 'password': base64.b64encode((self.passwd).encode("utf-8"))})
        url = 'http://' + self.hostname + '/bc_login?' + post_args
        req1 = Request(url)
        response = urlopen(req1)
        response_content = response.read()
        response_dict = json.loads(response_content.decode("utf-8"))
        if response_dict['status'] != 200:
            error_message = response_dict['message']
            raise Exception("Error {}: {}".format(
                response_dict['status'], error_message))
        self.cookie = response.headers.get('Set-Cookie')

    def send(self, command: str) -> bytes:
        """send a command to the BeeClear server and return the response data as bytes.
        Parameters:
            command : str
                The command to send, in the format "command_name?param1=value1&param2=value2".
        Returns:
            bytes
                The raw response data, as bytes."""
        url = 'http://' + self.hostname + '/' + command
        req = Request(url)
        # print(req)
        req.add_header('cookie', self.cookie)
        f = urlopen(req)
        data = f.read()
        f.close
        return data
    
    


    # import http.client

    # def send(self, command: str) -> bytes:
    #     """send a command to the BeeClear server and return the response data as bytes.
    #     Parameters:
    #         command : str
    #             The command to send, in the format "command_name?param1=value1&param2=value2".
    #     Returns:
    #         bytes
    #             The raw response data, as bytes."""
    #     url = '/' + command
    #     headers = {'cookie': self.cookie}
        
    #     conn = http.client.HTTPConnection(self.hostname)
    #     conn.request('GET', url, headers=headers)
    #     response = conn.getresponse()

    #     # Monitor the data stream
    #     data = b""
    #     while True:
    #         chunk = response.read(1024)
    #         if not chunk:
    #             break
    #         data += chunk
    #         print("Received chunk:", chunk)

    #     conn.close()
    #     return data

        
    
    def getbeeclear(command) -> dict:
        """convenience method that connects to the BeeClear server, sends a command,
        and parses the response data as a JSON object.
        Parameters:
            command : str
                The command to send, in the format "command_name?param1=value1&param2=value2".
        Returns:
            dict
                The response data, parsed as a JSON object."""
        a = beeclear(smartmeterconfig.host,
                        smartmeterconfig.username, smartmeterconfig.password)
        a.connect()
        Str_beeclear = a.send(command)
        # print(Str_beeclear)
        data = json.loads(Str_beeclear)
        return data


def returndata():
    """ returns a list of four values representing the current energy import and export.
        The function first gets the meter readings at midnight of the current date from the Beeclear API.
        It waits until the API returns non-empty data before proceeding. 
        Then, it retrieves the current meter readings from the API and calculates the energy imported and exported since midnight. 
        The calculated values are
        returned as a list with the following elements:
        1. Energy imported in watt-hour (Wh) since midnight
        2. Power imported in watt (W) currently
        3. Energy exported in watt-hour (Wh) since midnight
        4. Power exported in watt (W) currently
    Returns:
        list:
            A list of four values representing the energy import and export."""
    # data0 = {}
    # midnight = str(int(datetime.combine(
    #     datetime.now(), datetime.min.time()).timestamp()))  # calculate midnight date
    # while not bool(data0.get(['meetwaarden'][0])):
    #     data0 = beeclear.getbeeclear(
    #         'bc_getVal?type=elek&date='+midnight)  # values at midnight
    #     #  print (data0.get(['meetwaarden'][0]))
    #     time.sleep(3)       # sometimes it takes some time to receive the data

    # data = beeclear.getbeeclear("bc_current?nu='1683666589'&duration=8") 1683672576
    data = beeclear.getbeeclear("bc_getVal?type=elekw&date=1663670576")
    print(data) 
    ul0 = data0['meetwaarden'][0]['val'][0]['verbl']
    uh0 = data0['meetwaarden'][0]['val'][0]['verb']
    gl0 = data0['meetwaarden'][0]['val'][0]['levl']
    gh0 = data0['meetwaarden'][0]['val'][0]['lev']

    ul = data['ul']
    uh = data['uh']
    u = data['u']
    gl = data['gl']
    gh = data['gh']
    g = data['g']

    import_energy = (uh-uh0) + (ul-ul0)
    import_power = u
    export_energy = (gl-gl0) + (gh-gh0)
    export_power = g

    # meter_data = [import_energy, import_power, export_energy, export_power]
    meter_data = {"import_energy" : import_energy, "import_power" : import_power, "export_energy" : export_energy, "export_power" : export_power}

    return meter_data
    print (meter_data)
    
meter_data = returndata()
print (meter_data)
