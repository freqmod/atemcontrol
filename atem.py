#License: http://www.gnu.org/licenses/agpl.html
#(c) Frederik M.J. Vestre (ved/for Studentersamfundet i Trondheim)
#Based on perl code/reverse engineering by Michael Potter, 
#and reverse engineering with wireshark
#Blackmagic ATEM switch control
#Controls fader from midi input messages
#Midi messages not tested
#Works with Blackmagic ATEM television studio - standard config
#Midi requires pyportmidi
#Reverse engineering info:
#http://atemuser.com/forums/atem-vision-mixers/blackmagic-atems/controlling-atem
#http://sig11.de/~ratte/misc/atem/
from struct import pack, unpack
from binascii import hexlify, unhexlify
import socket
import random
import fcntl
import sys
import os
from time import sleep
has_midi = False
try:
    import pypm
    has_midi = True
except:
    pass
    
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
    #if not ln==12:
    #    print "Send:", hexlify(pkt)
    #    print_pkt(cmd, ln, uid, cout, un1, un2, cin, payload)
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
           hex(cnt_in), "Payload:",
           hexlify(payload))

midiin = None
if has_midi:
    print "Pre midi init"
    interf,name,inp,outp,opened = pypm.GetDeviceInfo(0)
    midiin = pypm.Input(0)
    print "Post midi init"

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
sock.setblocking(False)
while True:
    if midiin:
        midi_msg = midiin.Read(1) 
        if midi_msg:
            data, counter = midi_msg[0]
            bank, instrument, value, val2 = data
            print bank,instrument,value
    #        88 18 801c 01e1 0000 0000 01f7 - 000c 0000 4354 5073 0054 01f1 (Example pkg - value from 0-1000)
            payload = None
            if bank == 176 and instrument == 2:
                #Fader moved
                sval = value*7.87
                if sval<15:
                    sval=0
                elif sval>985:
                    sval=1000
                payload = pack("!HHHHHH", 0x000c, 0x0000,0x4354, 0x5073, 0x0054, sval)#value from 0-1000
                send_pkt(sock, 0x88, uid, cnt_in, 0, 0, mycnt, payload) 
                print "SENDFADE"
            if bank == 176 and instrument > 22  and instrument < 32 and value == 127:
                #top pressed
                payload = unhexlify("000c00004350674900")+chr(instrument-22)+unhexlify("0000")
                send_pkt(sock, 0x08, uid, cnt_in, 0, 0, mycnt, payload) 
                print "SENDTPKG"
            if bank == 176 and instrument > 32  and instrument < 42 and value == 127:
                #bottom pressed
                payload = unhexlify("000c00004350764900")+chr(instrument-32)+unhexlify("0000")
#                payload = unhexlify("000c00004350764900060000")
                send_pkt(sock, 0x08, uid, cnt_in, 0, 0, mycnt, payload) 
                print "SENDBPKG"
            if bank == 176 and instrument == 45 and value == 127:
                #bottom pressed
                payload = unhexlify("000c97024441757400000000")
#                payload = unhexlify("000c00004350764900060000")
                send_pkt(sock, 0x08, uid, cnt_in, 0, 0, mycnt, payload) 
                print "SENDATPKG"
            continue
    try:
        data = sock.recv(1024*10)
    except socket.error:
        sleep(0.02)
        continue
    if not data:
        print "Nodat"
        break;
#    print "Recv:", hexlify(data[0:16])
    args = recv_pkt(data)
    #print_pkt(*args)
    cmd, ln, uid, cnt_out, unkn1, unkn2, cnt_in, payload = args
    if not ln==12:
        print("R")
        print_pkt(*args)
    if cmd & 0x10:
        # hello response
        #undef, new_uid, undef, undef = unpack("!HHHH", payload)
        #uid = unpack("!HHHH", payload)[1]
        print "Helloresp", uid, cmd, cmd&0x10
#        send_pkt(sock, 0x80, uid, 0x0, 0, 0x00e9, 0, '')
        send_pkt(sock, 0x80, uid, 0, 0, 0x0050, 0, '')
        continue
    elif cmd & 0x08:
#        print "G8p", cnt_in, hello_finished
        if cnt_in == 0x04 and not hello_finished:
            hello_finished = True
            mycnt+=1
            print "Hellofinish"
        if hello_finished:
#            print "SHF"
            send_pkt(sock, 0x80, uid, cnt_in, 0, 0, 0, '')
            send_pkt(sock, 0x08, uid, 0, 0, 0, mycnt, '')
            mycnt+=1
#    else:
#        send_pkt(sock, 0x80, uid, 0, 0, mycnt, 0, '')
#        mycnt+=1

    #Read from command line
#    line = None
#    try:
#        line = sys.stdin.readline()
#    except:
#        pass
#    if line: #Send mixer info
##        88 18 801c 01e1 0000 0000 01f7 - 000c 0000 4354 5073 0054 01f1 (Example pkg)
#        payload = pack("!HHHHHH", 0x000c, 0x0000,0x4354, 0x5073, 0x0054, int(line))#value from 0-1000
#        send_pkt(sock, 0x88, uid, cnt_in, 0, 0, mycnt, payload) 
#
#    #Sett standard command number
    if (mycnt == 0 and hello_finished):
        cmd = 0x80
        

sock.close()
