import socket,sys
from threading import Thread  

#testing website http://open-up.eu   http://weevil.info/ 
#testing website https://my.tcd.ie

BUFFERSIZE = 4096
blockList = []
#cache and time are saved as dictionary, part of the info of the request will be key to identify each element
cache = {}    #save cache data
time = {}     #save cache time

#http request handler
def http(desthost,destport,data,client):
    try:
        #create a new socekt
        httpS = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        #connect the socket with destination server
        httpS.connect((desthost,int(destport)))
        #print("Successfully connected!")
        #forward the data to the server
        httpS.sendall(data)
        #httpS.setblocking(0)
        #client.setblocking(0)
        working = True
        while working:
            try:
                #receive data from server
                response = httpS.recv(BUFFERSIZE)
                if(len(response)<=0):
                    working = False
                #send the data to browser
                client.sendall(response)
            except BlockingIOError:
                break
        #finish forward data and close the sockets
        httpS.close()
        client.close()
    except KeyboardInterrupt:
        userInputHandler(httpS,client)

#http request handler but will save caches
def httpwithcache(desthost,destport,data,client):
    try:
        #set key to the first line of the request which contains hostname, portnumber
        detail = str(data.decode()).split("\r\n")
        key = detail[0]
        httpS = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        httpS.connect((desthost,int(destport)))
        httpS.sendall(data)
        #initialize cache to empty
        working = True
        cachedata = b""
        while working:
            try:
                #receive data from server
                response = httpS.recv(BUFFERSIZE)
                cachedata = cachedata + response
                if(len(response)<=0):
                    working = False
                #send the data to browser
                client.sendall(response)
            except OSError:
                pass
            except BlockingIOError:
                break
        realtime = timeformat()
        cache[key] = cachedata
        time[key] = realtime
        httpS.close()
        client.close()
    except KeyboardInterrupt:
        userInputHandler(httpS,client)
    except Exception:
        pass

#https request handler
def https(desthost,destport,data,client):
    try:
        #create a new socket
        httpsS = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        #httpsS.settimeout(10000)
        #when response to the client to make the response secure, send it in plain text instead of the actual data
        responsetoclient = b"HTTP/1.0 200 Connection Established\r\nProxy-agent: Pyx\r\n\r\n"
        client.send(responsetoclient)
        httpsS.connect((desthost,int(destport)))
        #set socket to unblocking, because the default is blocking
        httpsS.setblocking(0)
        client.setblocking(0)
        while True:
            #check if there are requests need to send to server
            try:
                #receive request from client
                requesttoserver = client.recv(BUFFERSIZE)
                #print("Successfully connected with HTTPS!")
                if(len(requesttoserver)<=0):
                    break
                #send client requests to server
                httpsS.sendall(requesttoserver)
            except:
                pass
            #if no requests to server, check if there are responses need to send to client
            try:
                #receive response from server
                responsetoclient = httpsS.recv(BUFFERSIZE)
                #print("Response recieved!" + desthost)
                if(len(responsetoclient)<=0):
                    break
                #send server response to client
                client.sendall(responsetoclient)
            except:
                pass
    except KeyboardInterrupt:
        userInputHandler(httpsS,client)

#filter the requests and send to different handler
def connectClient(data, client):
    try:
        #decode the request message to check if it is HTTP request or HTTPS request
        datapiece = str(data.decode()).split("\r\n")
        isHTTPS = False
        #HTTP request starts from "GET" and HTTPS request starts from "CONNECT"
        if datapiece[0].startswith("CONNECT") :
            isHTTPS = True
        #search in datapiece for destnation host and its port number
        i = 0
        hosti = 0
        for pieces in datapiece:
            #if the fist four letter is Host, save the index (position in datapiece)
            if(pieces[:4] == "Host"):
                hosti = i
            i = i + 1
        #the info of the desthost is at the position hosti in datapiece
        #and delete "Host: " the substring starts from 6
        desthost = datapiece[hosti][6:]
        tmp = ""
        if(desthost.find(":")==-1):
            tmp = desthost
        else:
            tmp = desthost.split(":")[0]
        #check if the desthost is in the blocklist
        if(tmp not in blockList):
            #print the request pretty
            for string in datapiece:
                print('\x1b[0;34;40m' + string + '\x1b[0m')
            #now desthost contains: hostname(:port)
            #if there is ":" the port number is given
            #if not, set http port number to 80 and https port number to 443
            portgiven = desthost.find(":")
            destport = 0
            #if : is not found, portgiven is -1
            if(portgiven == -1 and isHTTPS == False):
                destport = 80  #default http port
            elif(portgiven == -1 and isHTTPS == True):
                destport = 443  #default https port
            else:
                destport = desthost.split(":")[1]
                desthost = desthost.split(":")[0]
            #now desthost and destport are got, start the transmission
            #print("destination host is " + desthost + " and its port is ", destport)
            
            usecache = True
            if(usecache==True):
                if(isHTTPS==True):
                    https(desthost, destport, data, client)
                else:
                    key = datapiece[0]
                    message = caching(desthost,destport,key,data,client)
                    #send the respond message to client
                    if (message==1): #sent cache
                        #client.sendall(message)
                        print("cache sent")
                        #client.close()
                    else:
                        #there is no cache in the cache list, handle the requests
                        httpwithcache(desthost, destport, data, client)
            else:
                #test for no caching handlers
                if(isHTTPS == False):
                    http(desthost, destport, data, client)
                else:
                    https(desthost, destport, data, client)
        #the desthost is blocked, output selfdesigned host blocked page
        else:
            print("This host is blocked")
            message = "HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body>This host is blocked.</body></html>\r\n\r\n"
            client.sendall(message.encode())
            client.close()
    except KeyboardInterrupt:
        userInputHandler(client)

#the start of this proxy server, bind with localhost
def createProxyServer():
    try:
        #create a socket for proxy server
        proxy = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        #reuse the socket
        proxy.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        #bind the socket with local host and given a port number 7000
        proxy.bind(('localhost',7000))
        #listen for the connection requests, 5 requests can exist together
        #deal with 1 and the other 4 will be queuing
        proxy.listen(10)
        print("socket created successfully")
        print("Listening")
    except:
        print("socket creation failed")
    while True:
        try:
            #accept browser connection request and return the requesting socket and address
            (client,address) = proxy.accept()
            #receive the data from the request, maximum 1024 bytes, data stored as string
            data = client.recv(BUFFERSIZE)
            #print(data.decode())
            #create thread to deal with the requests and responses
            thread=Thread(target = connectClient, args = (data,client))
            #set daemon of the thread to True
            thread.daemon=True
            #start the thread's activity
            thread.start()
        except OSError:
            pass
        except KeyboardInterrupt:
            userInputHandler()

#handle caching information, check or update caches
def caching(desthost,destport,key,data,client):
    #initialize response
    response = b''
    #if infomation has been cached
    if key in cache:
        #cache found, create a new socket and now proxy is the server
        proxy = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        #connect with host
        proxy.connect((desthost,int(destport)))
        #get the response from the cache
        print("cached data")
        #for string in info:
        #    print('\x1b[0;34;40m' + string + '\x1b[0m')
        response = cache[key]
        pieces = str(data.decode()).split("\r\n")
        #for string in pieces:
        #    print('\x1b[0;34;40m' + string + '\x1b[0m')
        #find last modified date and update it
        i=0
        for piece in pieces:
            if(piece.startswith("If-Modified-Since:")):
                pieces[i] = "If-Modified-Since: " + str(time[key])+"\r\n"
                print(pieces[i])
                break
            i = i+1
        print("UPDATED " + str(key))
        print()
        #put update pieces together to be ready to send back to client
        message = ""
        for piece in pieces:
            if piece is not '':
                new = piece + "\r\n"
                message = message + new
        
        #encode the message and send to client to see if there is 304 in reply
        proxy.sendall(message.encode())
        #get response from client
        newresponse = proxy.recv(BUFFERSIZE)
        signal = b'HTTP/1.0 304 Not Modified\r\n'
        #if reply contains 304 Not Modified return the cache
        if newresponse.find(signal)>-1:
            print("SUCCESS")
            client.sendall(cache[key])
            client.close()
            proxy.close()
            return 1
        #else recieve new data
        else:
            proxy.close()
            return 2
    else:
        return 0

#the format of time for "If-Modified-Since"
def timeformat():
    #format is Tue, 18 Aug 2015 15:44:04
    now = datetime.now()
    daymonth = now.strftime("%d %B")
    time = now.strftime(" 20%y %H:%M:%S")
    day = now.strftime("%A")
    return day[:3]+", "+daymonth[:6]+time+" GMT"

#managable console to handle user inputs
def userInputHandler(*sockets):
    choice = input("\nIf you want to exit, please enter \"exit\"\
                    \nIf you want to block a url, please enter \"block (your host)\"\
                    \nIf you want to unblock a url, please enter \"unblock (your host)\"\
                    \nIf you want to see the url blocking list, please enter \"show block list\"\n")
    if (choice == "exit") :
        close(sockets)
    elif (choice[:5] == "block"):
        #check if the url is in the block list
        #if it is not, add the url to block list
        #reply a message successfully blocked url
        url = choice[6:]
        i=0
        for burl in blockList:
            if(burl == url):
                print("This host \""+url+"\" is already blocked")
            i = i+1
        if (i==len(blockList)):
            blockList.append(url)
            print("Successfully blocked given host")
    elif(choice[:7] == "unblock"):
        #check if the url is in the block list
        #if it is in, unblock it and tell user it is successfully unblocked
        #if not, reply message to user that it is not locked
        url = choice[8:]
        i=0
        remove = False
        for burl in blockList:
            if(burl==url):
                blockList.remove(url)
                print("Successfully removed given host")
                remove=True
                break
            i=i+1
        if(i==len(blockList) and remove==False):
            print("Your host is not blocked")
    elif (choice == "show block list"):
        #print out the block url list
        for url in blockList:
            print(url)
            print()
    else:
        print("Invalid input")

#when user chose to exit, close all the sockets
def close(*sockets):
    #if there are sockets passing to the function, close the sockets
    if len(sockets)>0:
        for s in sockets:
            if s:
                s.close()
    print("Mission completed, shutting down")
    print("Bye")
    sys.exit()

createProxyServer()    
