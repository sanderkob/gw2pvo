#!/usr/bin/python
"""Connects to Beeclear device ( https://forum.beeclear.nl/attachment.php?aid=35 )
       and downloads json, format https://www.beeclear.nl/docs/bc_api0.0.4.pdf    """

from urllib.parse import urlencode
from urllib.request import Request, urlopen
import base64
import json
import config #stores host, username, password
from datetime import datetime
import time
# from nested_lookup import nested_lookup

class beeclear:
    def __init__( self, hostname, user, passwd ):
        self.hostname = hostname
        self.user = user
        self.passwd = passwd
        self.cookie = None;
    def connect( self ):
        post_args = urlencode( { 'username': base64.b64encode((self.user).encode("utf-8")), 'password': base64.b64encode((self.passwd).encode("utf-8")) } )
        url = 'http://' + self.hostname + '/bc_login?' + post_args;
        req1 = Request(url)
        response = urlopen(req1)
        self.cookie = response.headers.get('Set-Cookie')
    def send( self, command ):
        url = 'http://' + self.hostname + '/' + command
        req = Request(url)
        req.add_header('cookie', self.cookie)
        f = urlopen(req)
        data = f.read()
        f.close
        return data
    def getbeeclear(command):
        a = beeclear( config.host, config.username, config.password )
        a.connect()
        Str_beeclear = a.send (command)#&duration=day&period=hour')#&duration=day&period=hour
        data = json.loads (Str_beeclear)
        local_time = datetime.now () #utc_time.astimezone()
        # print(local_time.strftime("%H:%M:%S %d-%m-%Y"))
        return data
    
def returndata():
        data0 = {}
        midnight = str(int(datetime.combine(datetime.now(),datetime.min.time()).timestamp()))  # calculate midnight date
        while not bool(data0.get(['meetwaarden'][0])):
            data0 = beeclear.getbeeclear('bc_getVal?type=elek&date='+midnight) # values at midnight
            #  print (data0.get(['meetwaarden'][0]))
            time.sleep(3)       # sometimes it takes some time to receive the data

        data = beeclear.getbeeclear('bc_current')
        ul0=data0['meetwaarden'][0]['val'][0]['verbl']
        uh0=data0['meetwaarden'][0]['val'][0]['verb']
        gl0=data0['meetwaarden'][0]['val'][0]['levl']
        gh0=data0['meetwaarden'][0]['val'][0]['lev']

        ul=data['ul']
        uh=data['uh']
        u=data['u']
        gl=data['gl']
        gh=data['gh']
        g=data['g']
#        print (type(uh0))
#        print (uh0)
#        print (ul0)
#        print (uh)
#        print (ul)
#        print (u)
#        print (uh-uh0)
#        print (ul-ul0)
        cons_wh = (uh-uh0) + (ul-ul0)
        cons_w = u
        sup_wh = (gl-gl0) + (gh-gh0)
        sup_w = g
#        print (cons_wh, cons_w)
        cons = [cons_wh, cons_w, sup_wh, sup_w]
#        print (cons)
        return cons
