from struct import pack, unpack
from binascii import hexlify, unhexlify
import socket
import random
import fcntl
import sys
import os
HOST = '192.168.10.240'    # The remote host
PORT = 9910              # The same port as used by the server
def rand(max):
    return int(random.uniform(0,max))
    
def send_hello(sock):
    uid   = (((rand(254) + 1) << 8) + rand(254) + 1) & 0x7FFF
#    uid = 0x67a5
    data  = pack("!HHHH", 0x0100, 0x0000, 0x0000, 0x0000)
    print "Data", hexlify(data)
    hello = pack("!BBHHHHH", 0x10, 0x14, uid, 0, 0, 0x0000, 0) + data
    print "Hello:", hexlify(hello)
    #101454b200000000000000000100000000000000

    sock.send(hello)
    return uid
    
def send_pkt(sock, cmd, uid, cout, un1, un2, cin, payload):
    ln = 12 + len(payload)
    cmd += ((ln >> 8) & 0x07)
    pkt = pack("!BBHHHHH", cmd, ln, uid, cout, un1, un2, cin) + payload
    print "Send:", hexlify(pkt)
    sock.send(pkt)

def recv_pkt(data):
    pkt = data
    cmd, len, uid, cnt_out, unkn1, unkn2, cnt_in = unpack("!BBHHHHH", data[0:12])
    payload = data[12:]
    #(port, ipaddr) = sockaddr_in($sock->peername)
    len = ((cmd & 0x07) << 8) + len
    cmd = cmd & 0xF8
    return (cmd, len, uid, cnt_out, unkn1, unkn2, cnt_in, payload)

def print_pkt(cmd, len, uid, cnt_out, unkn1, unkn2, cnt_in, payload):
    print ("Cmd:",
           hex(cmd), "Len:",
           len, "Uid:",
           hex(uid), "Unkn1:",
           unkn1, "Unkn2:",
           unkn2, "Cnti:", 
           hex(cnt_in), )
#           hexlify(payload))


# make stdin a non-blocking file
fd = sys.stdin.fileno()
fl = fcntl.fcntl(fd, fcntl.F_GETFL)
fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.connect((HOST, PORT))
uid = send_hello(sock)
#sock.send(unhexlify("1014439d00000000000000000100000000000000"))
#800c67a50000000000500000
print uid
mycnt = 0
hello_finished = False
while True:
    data = sock.recv(1024*10)
    if not data:
        print "Nodat"
        break;
    print "Recv:", hexlify(data[0:16])
    args = recv_pkt(data)
    print_pkt(*args)
    cmd, ln, uid, cnt_out, unkn1, unkn2, cnt_in, payload = args
    if cmd & 0x10:
        # hello response
        #undef, new_uid, undef, undef = unpack("!HHHH", payload)
        #uid = unpack("!HHHH", payload)[1]
        print "Helloresp", uid, cmd, cmd&0x10
#        send_pkt(sock, 0x80, uid, 0x0, 0, 0x00e9, 0, '')
        send_pkt(sock, 0x80, uid, 0, 0, 0x0050, 0, '')
        continue
    elif cmd & 0x08:
        print "G8p", cnt_in, hello_finished
        if cnt_in == 0x04 and not hello_finished:
            hello_finished = True
            mycnt+=1
            print "Hellofinish"
        if hello_finished:
            print "SHF"
            send_pkt(sock, 0x80, uid, cnt_in, 0, 0, 0, '')
            send_pkt(sock, 0x08, uid, 0, 0, 0, mycnt, '')
            mycnt+=1
#    else:
#        send_pkt(sock, 0x80, uid, 0, 0, mycnt, 0, '')
#        mycnt+=1
    line = None
    try:
        line = sys.stdin.readline()
    except:
        pass
#    print "Line:", line,"<"
    if line:
        print "Kake"
#        88 18 801c 01e1 0000 0000 01f7 - 000c 0000 4354 5073 0054 01f1
        payload = pack("!HHHHHH", 0x000c, 0x0000,0x4354, 0x5073, 0x0054, int(line))
        send_pkt(sock, 0x88, uid, cnt_in, 0, 0, mycnt, payload) 
    if (mycnt == 0 and hello_finished):
        cmd = 0x80
        

sock.close()
