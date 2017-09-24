#!/usr/bin/env python
"""
Very basic web access to log and queue monitor for ARM (Automatic Ripping Machine) https://github.com/ahnooie/automatic-ripping-machine


Usage::
    Place script in /opt/arm directory 
    sudo ./logserve.py [<port>]

View the empty.log in reverse order::
    http://localhost:[port]
    
View the Info page
    http://localhost:[port]/info/

Thanks to derex99 for the disc favicon
 derex99 - Own work, CC BY-SA 3.0, https://commons.wikimedia.org/w/index.php?curid=3836116

"""
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import SocketServer
import os
import subprocess

def getconfig(searchstring):
    with open('config', 'r') as searchfile:
        for line in searchfile:
            if searchstring in line:
                line = line.split("=")[1].strip()
		line = line[1:-1]
		return line

LOGPATH = getconfig("LOGPATH=")
LOGFILE = LOGPATH + "empty.log"
RAWPATH = getconfig("RAWPATH=")
ARMPATH = getconfig("ARMPATH=")

def getsize(path)
    st = os.statvfs(path)
    free = (st.f_bavail * st.f_frsize)
    freegb = free/1073741824
    return freegb

class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def info(self):
        freeraw = getsize(RAWPATH)
	    freearm = getsize(ARMPATH)
        output = subprocess.check_output("atq | perl -lane 'print $F[0]'", shell=True)
        self.wfile.write("<html><head><title>ARM Status</title><meta http-equiv=\"refresh\" content=\"60\"><style>table {font-family: arial, sans-serif;border-collapse: collapse;width: 100%;}td, th {border: 1px solid #dddddd;text-align: left;padding: 8px;}tr:nth-child(even) {background-color: \#dddddd;}</style></head><body><h1>Disk Info</h1>")
        self.wfile.write("<h2>" + str(freeraw) + " GB free for ripping</h2>")
        self.wfile.write("<h2>" + str(freearm) + " GB free for transcoding</h2>")
        self.wfile.write("<html><body><h1>Queue Items</h1><table><tr><th>Queue Number</th><th>Command</th></tr>")
        for line in output.split():
            item = subprocess.check_output("at -c {0} | tail -n 2".format(line), shell=True)
	        self.wfile.write("<tr><td>" + line + "</td><td>" + item + "</td></tr>")
        self.wfile.write("</table></body></html>")

    def do_GET(self):
	# There is special handling for http://127.0.0.1/info. That URL
        # displays some internal information.
        if self.path == '/info' or self.path == '/info/':
            self._set_headers()
            self.info()
        elif self.path == '/favicon.ico':
            self.send_response(200)
            self.send_header('Content-type','image/jpeg')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with open("favicon.ico", "rb") as fout:
                self.wfile.write(fout.read())
        else:
            self._set_headers()
            contents = open(LOGFILE,"r")
            self.wfile.write("<html><body><h1>ARM Log</h1><pre>")
	        for lines in reversed(contents.readlines()):
                self.wfile.write(lines + "<br>\n")
            self.wfile.write("</pre></body></html>")

    def do_HEAD(self):
        self._set_headers()
        
    def do_POST(self):
        # Doesn't do anything with posted data
        self._set_headers()
        self.wfile.write("<html><body><h1>POST!</h1></body></html>")
        
def run(server_class=HTTPServer, handler_class=S, port=80):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print 'Starting httpd...'
    httpd.serve_forever()

if __name__ == "__main__":
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()