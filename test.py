#!/usr/bin/env python

import socket, sys, threading
from httplib import HTTPResponse
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO

serverAddr = '127.0.0.1'

class FakeSocket():
    def __init__(self, response_str):
        self._file = StringIO(response_str)
        self.y = 0
    def update_y(self):
        self.y = self.y + 1
    def makefile(self, *args, **kwargs):
        self.update_y()
        return self._file

class HTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, request_text):
        self.rfile = StringIO(request_text)
        self.raw_requestline = self.rfile.readline()
	self.x = 1
        self.error_code = self.error_message = None
        self.parse_request()

    def update_x(self):
	self.x = self.x + 1

    def send_error(self, code, message):
        self.error_code = code
	self.myerror = message
        self.error_message = message
	self.update_x()

# class TheServer:
maxCon = 500 # backlog for the sever
active_cons = {} # dictionary for active connections
cache = {} # cache data for faster reply
buffer_size = 4096 # set buffer size to 4 KB
timeout = 20 #set timeout to 2 seconds
port = 0
address = 0
server = 0 
def initial(host, port_no):
    	global port,address,server,maxCon,active_cons,cache,buffer_size,timeout
        """ Initialise my the server """
        try:
            port = port_no
            address = host
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((host, port))
            server.listen(maxCon)
            print("Proxy Server has started successfully. hence it willl be Listening on port: " + str(port) + "\n")
        except Exception as e:
            print("Error => Can not bind socket: " + str(e))
            print("Exiting application...shutting down")
            shutdown()

def main_loop():
    global port,address,server,maxCon,active_cons,cache,buffer_size,timeout
    """ Listen for incoming connections """
        
    print("Listening incoming connections...\n")
    while 1:

            # Establish the connection
        try:
            clientSocket, client_address =  server.accept()
        except Exception as e:
            print("Error on accepting connection from client: " + str(e))
            continue
        print("\nAccepted connection from " + ':'.join(str(i) for i in client_address))

        active_cons.update({clientSocket : client_address})
            
        d = threading.Thread(name = client_address[0],target = proxy_thread, args=(clientSocket,))
        d.setDaemon(True)
        d.start()

def close_client(conn):
    global port,address,server,maxCon,active_cons,cache,buffer_size,timeout
    lk = threading.Lock()
    lk.acquire()
    client_info = active_cons.pop(conn)
    lk.release()
    conn.close()

def parse_request(request):
    global port,address,server,maxCon,active_cons,cache,buffer_size,timeout
    """ Parse request from cient """
    
    try:
        req = HTTPRequest(request)
        if req.command == 'CONNECT':
            print("Unsupported request type. Currently this proxy server doesn't handles CONNECT requests :(")
            return (0, 0, 0, 0)
        if 'host' in req.headers:
            remote_host = req.headers['host']
        else:
            remote_host = None
        if req.path.startswith('http'):
            if remote_host is None:
                remote_host = req.path.replace('http://', '').split(':')[0].strip('/')
            cachekey = req.command + ':' + req.path.strip('/')
            try:
                remote_port = int(requrl.split(':')[2])
            except:
                remote_port = 80
        else:
            if remote_host is None and req.path.startswith('/'):
                print("Invalid request!!")
                return(0, 0, 0, 0)
            else:
                remote_host = req.path.split(':')[0].strip('/')
            cachekey = req.command + ':' + 'http://' + remote_host + req.path.strip('/')
            try:
                remote_port = int(requrl.split(':')[1])
            except:
                remote_port = 80
    except Exception as e:
        print("Error in parsing request: " + str(e))
        return(0, 0, 0, 0)
        
    return (remote_host, remote_port, cachekey, 1)


def proxy_thread(conn):
        global port,address,server,maxCon,active_cons,cache,buffer_size,timeout
        """ Thread to handle requests from client/browser """

        curr_client = ':'.join(str(i) for i in active_cons[conn])
        print("Started new thread for " + curr_client)
                
        try:
            request = conn.recv(buffer_size) # get request from client
        except Exception as e:
            print("Error in receiving request from the client: " + curr_client + ". Closing Connection...")
            close_client(conn)
            return
        print("Received request:\n" + request)

        remote_host, remote_port, cachekey, valid = parse_request(request)
        if not valid:
            close_client(conn)
            return

        if cachekey in cache:
            # key found in cache, return data from cache
            
            relay_to_client(conn, 0, cachekey, 1)
            close_client(conn)
            return

        remote_socket = relay_to_remote(remote_host, remote_port, request)
        if remote_socket:
            response = relay_to_client(conn, remote_socket)
            if response:
                cache_storage(cachekey, response)
        else:
            print("Closing connection with client: " + curr_client)
        
        close_client(conn)


def relay_to_remote(remote_host, remote_port, request):
        global port,address,server,maxCon,active_cons,cache,buffer_size,timeout        
        """ Relay the request from client to the remote server """

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((remote_host, remote_port))
            s.sendall(request)
            return s
        except Exception as e:
            print("Cannot relay data to the remote server: " + remote_host + ':' + str(remote_port))
            print("Error: " + str(e))
            return False

def relay_to_client(client_sock, remote_sock, cachekey = '', cache_check = 0):
        global port,address,server,maxCon,active_cons,cache,buffer_size,timeout        
        """ Relay the response from remote server to the client """
        
        data = ''
        if cache_check:
            client_sock.send(cache[cachekey])
            return True
        
        try:
            data = remote_sock.recv(buffer_size)
        except Exception as e:
            print("Error in receving response from the remote server. " + str(e))
            return False
        d = data
        while len(d) > 0:
            client_sock.send(d)
            d = remote_sock.recv(buffer_size)
            if (len(d) <= 0):
                break
            data += d
        return data

def parse_response(response):
        global port,address,server,maxCon,active_cons,cache,buffer_size,timeout       
        """ Check if the response is valid to stored in cache """
        try:
            source = FakeSocket(response)
            parsed_response = HTTPResponse(source)
            parsed_response.begin()
        except Exception as e:
            print("Error in parsing response. " + str(e))
            return 0
        sc = parsed_response.status # status-code
        try:
            cc = parsed_response.getheader("Cache-Control").split(',') # cache-control
        except:
            cc = []
        pragma = parsed_response.getheader("Pragma")
        if sc == 302 or sc == 301 or sc == 200 or sc == 304:
            if 'no-cache' in cc or 'private' in cc or 'no-store' in cc or pragma == 'no-cache':
                return 0
            else:
                return 1
        else:
            return 0

def cache_storage(cachekey, response):
        global port,address,server,maxCon,active_cons,cache,buffer_size,timeout
        """ Store the response in cache """

     
        if parse_response(response):
            lk = threading.Lock()
            lk.acquire()
            try:
                
                cache.update({cachekey : response})
                #self.cache.update({cachekey : response + "\n\n***Serving from cache***\n\n"})
            finally:
                lk.release()
       

def shutdown():
        global port,address,server,maxCon,active_cons,cache,buffer_size,timeout
        """ Clear all data from the server """

        for i in active_cons:
            i.close() # close all the active cons with the proxy
        server.close() # close the proxy socket

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("incorrect format :")
        sys.exit(1)
    port = int(sys.argv[1])
    initial(serverAddr, port)
    try:
        main_loop()
    except KeyboardInterrupt:
        print("User requested interrupt.\nExiting...")
        shutdown()
