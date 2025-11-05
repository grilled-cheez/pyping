import socket
import os
import sys
import time
import ctypes
import struct
import select

if sys.platform.startswith("win32"):
    default_timer = time.clock
else:
    default_timer = time.time

ICMP_ECHO_REQUEST = 8  # Platform specific
MAX_HOPS = 30
TIMEOUT = 4
TRIES = 15


# check for admin/root privileges
def check_admin():

    try:
        return os.getuid() == 0  # for linux/unix/mac
    except AttributeError:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

if not check_admin():
    # print("You need to run this program as administrator!")
    print("Admin baney phir istemaal karey. Me jaa rha bye...")
    sys.exit(1)

def checksum(srcstr):
    s = 0
    countto = (len(srcstr) // 2) * 2
    count = 0

    while count < countto:
        thisval = srcstr[count+1] * 256 + srcstr[count]
        s += thisval
        s = s & 0xffffffff  # Necessary? limits to 32 bits
        count += 2

    if countto < len(srcstr):
        s +=  srcstr[len(srcstr) - 1]
        s = s & 0xffffffff  # Necessary? limits to 32 bits
    # folding 32 bits to 16 bits

    s = (s >> 16) + (s & 0xffff)
    s += s>>16
    res = ~s #complement
    res = res & 0xffff

    res = res >> 8 | (res << 8 & 0xff00)
    return res

def createpkt(pid, seq):
    # header is type (8), code (8), checksum (16), id (16), sequence (16)

    header  = struct.pack("bbHHh", ICMP_ECHO_REQUEST,0, 0, pid, seq)
    data = struct.pack("d", default_timer())
    mychecksum = checksum(header + data)
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(mychecksum), pid, seq)

    return header + data

def pingonce(sock, dest, pid, seq):
    pkt = createpkt(pid, seq)
    sock.sendto(pkt, (dest, 1)) # Port number is irrelevant for ICMP
    start_time = default_timer()
    try:
        ready = select.select([sock], [], [],  TIMEOUT)
        if ready[0] == []:
            print("Request timed out for {seq}".format(seq=seq))
            return None
        
        recv_pkt, addr = sock.recvfrom(1024)
        end_time = default_timer()

        time_sent = struct.unpack("d", recv_pkt[28:36])[0]
        rtt  = (end_time - time_sent) * 1000

        ttl = recv_pkt[8]

        print(f'reply from {addr[0]}: bytes={len(recv_pkt)} time={round(rtt, 2)}ms TTL={ttl}')
        return rtt

    except socket.timeout:
        print("Request timed out for {seq}".format(seq=seq))
        return None
    
    except Exception as e:
        print("General error: {}".format(e))
        return None 

def ping(host):
    try :
        dest = socket.gethostbyname(host)
    except socket.gaierror:
        print("Dont know about this host. Check karo naam sahi hai ki nahi.")
        return None

    print("Pinging " + dest + " using Python:")

    pid = os.getpid() & 0xFFFF
    rtts = []
    sent = 0
    received = 0

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname("icmp")) as sock:
            sock.settimeout(TIMEOUT)

            for seq in range(1, TRIES+1):
                sent += 1
                rtt = pingonce(sock, dest, pid, seq)
                if rtt:
                    rtts.append(rtt)
                    received += 1
                time.sleep(1)
            
    except PermissionError:
        print("You need to run this program as administrator!")
        sys.exit(1)

    except Exception as e:
        print("General error: {}".format(e))

    # end of pinging
    print("\n---- Ping stats ----")
    print("{sent} packets transmitted, {received} packets received, {loss}% packet loss".format(
        sent=sent, received=received, loss=round(((sent-received)/sent)*100, 2)
    ))

    if rtts:
        print("Approximate round trip times in milli-seconds:")
        print("Minimum = {min}ms, Maximum = {max}ms, Average = {avg}ms".format(
            min=round(min(rtts), 2),
            max=round(max(rtts), 2),
            avg=round(sum(rtts)/len(rtts), 2)
        ))

if __name__ == "__main__":
    cmd = input()
    if cmd.startswith("ping "):

        target = cmd.split('ping ')[1]
        ping(target)
    else:
        print("kripya dhang se likhe: ping <hostname>")