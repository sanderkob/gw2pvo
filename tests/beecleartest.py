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
            Connects to the server, authenticates the user with the provided credentials.
        send(command: str) -> bytes:
            Send a command to the BeeClear server and return the response data as bytes.
        getbeeclear(command: str) -> dict:
            Connects to the BeeClear server, sends a command, and parses the response as JSON.
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
        """connect to the BeeClear server and authenticate the user
        with the provided credentials.
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
                command to send, in the format "command_name?param1=value1&param2=value2".
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

    # test met httpclient
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
        """method to connects to the BeeClear server, sends a command
        and parses the response data as a JSON object.
        Parameters:
            command : str
                command to send, in the format "command_name?param1=value1&param2=value2".
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
    """ returns a JSON object 
    Returns:
        dict:
            raw data from the Beeclear server"""

    data = beeclear.getbeeclear("bc_getVal?type=elekw&date=1663670576")
    return data


# run command
print(returndata())
