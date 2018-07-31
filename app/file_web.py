#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/16 9:19
# @Author  : LiangLiang
# @Site    : 
# @File    : file_web.py
# @Software: PyCharm

from flask import Flask, request, render_template
import csv
import copy
import json
from pymysql import connect
import random
import os
import sys
import time
from subprocess import Popen,PIPE
from twisted.internet import protocol
dirpath = os.path.abspath(os.path.dirname(__file__))
from flask_twisted import Twisted
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor
import hashlib,struct
from base64 import b64decode,b64encode
from copy import deepcopy
import re



app = Flask("fileweb")


class machine_heart_beat(protocol.Protocol):
    def dataReceived(self, data):
        data2 = getCPU_info()
        # data2 = "你好你好，你好你好你好你好你好！！！！！！！！！！！！！！！！！！！！"
        headers = {}

        def set_bit(int_type, offset):
            return int_type | (1 << offset)

        def pack2(message):
            msgLen = len(message)
            backMsgList = []
            backMsgList.append(struct.pack('B', 129))

            if msgLen <= 125:
                backMsgList.append(struct.pack('b', msgLen))
            elif msgLen <= 65535:
                backMsgList.append(struct.pack('b', 126))
                backMsgList.append(struct.pack('>h', msgLen))
            elif msgLen <= (2 ^ 64 - 1):
                backMsgList.append(struct.pack('b', 127))
                backMsgList.append(struct.pack('>h', msgLen))
            else:
                print("the message is too long to send in a time")
                return
            message_byte = bytes()
            # print(type(backMsgList[0]))
            for c in backMsgList:
                # if type(c) != bytes:
                # print(bytes(c, encoding="utf8"))
                message_byte += c
            message_byte += bytes(message, encoding="utf8")
            return message_byte

        def parse_recv_data(msg):
            en_bytes = b''
            cn_bytes = []
            if len(msg) < 6:
                return ''
            v = msg[1] & 0x7f
            if v == 0x7e:
                p = 4
            elif v == 0x7f:
                p = 10
            else:
                p = 2
            mask = msg[p:p + 4]
            data = msg[p + 4:]

            for k, v in enumerate(data):
                nv = chr(v ^ mask[k % 4])
                nv_bytes = nv.encode()
                nv_len = len(nv_bytes)
                if nv_len == 1:
                    en_bytes += nv_bytes
                else:
                    en_bytes += b'%s'
                    cn_bytes.append(ord(nv_bytes.decode()))
            if len(cn_bytes) > 2:
                # 字节数组转汉字
                cn_str = ''
                clen = len(cn_bytes)
                count = int(clen / 3)
                for x in range(0, count):
                    i = x * 3
                    b = bytes([cn_bytes[i], cn_bytes[i + 1], cn_bytes[i + 2]])
                    try:
                        cn_str += b.decode()
                    except Exception as e:
                        print(e)
                new = en_bytes.replace(b'%s%s%s', b'%s')
                new = new.decode()
                res = (new % tuple(list(cn_str)))
            else:
                res = en_bytes.decode()
            return res

        if self.handshaken == False:
            # print('Start Handshaken with {}!'.format(self.remote))
            self.buffer += bytes.decode(data)
            if self.buffer.find('\r\n\r\n') != -1:
                header, data = self.buffer.split('\r\n\r\n', 1)
                for line in header.split("\r\n")[1:]:
                    key, value = line.split(": ", 1)
                    headers[key] = value

                headers["Location"] = ""
                key = headers['Sec-WebSocket-Key']
                token = b64encode(hashlib.sha1(str.encode(str(key + self.GUID))).digest())

                handshake = "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: " + bytes.decode(
                    token) + "\r\nWebSocket-Origin: " + str(headers["Origin"]) + "\r\nWebSocket-Location: " + str(
                    headers["Location"]) + "\r\n\r\n"

                self.transport.write(handshake.encode("utf-8"))
                self.handshaken = True
                return
                # print('Handshaken with {} success!'.format(self.remote))

        data_raw = parse_recv_data(data)
        print(data_raw)

        count1 = 0
        # print(self.stas._stats)
        # stats_info = data2.encode("utf-8")
        # stats_info['start_time'] = stats_info['start_time'].strftime("%Y-%m-%d %H:%M:%S")
        #
        jsonstr = json.dumps(data2)
        self.transport.write(pack2(jsonstr))

    def connectionMade(self):
        print("a connection has been built")
        self.handshaken = False
        self.buffer = ""
        self.GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def connectionLost(self, reason=None):
        print("a connection has closed")


class Factory(protocol.Factory):
    protocol = machine_heart_beat()
    def buildProtocol(self, addr):
        return machine_heart_beat()


endpoint = TCP4ServerEndpoint(reactor=reactor,port=8844)
endpoint.listen(Factory())


def getCPU_info():
    a = time.time()
    Re_find_loadaverge = re.compile("(\d+) user.*load average: (\d+\.\d*)\, (\d+\.\d*)\, (\d+\.\d*)")
    Re_find_task = re.compile("Tasks\: (\d+) total\,\s*(\d+)\srunning\,\s(\d+)\ssleeping\,\s*(\d+)\sstopped\,\s*(\d+)\szombie")
    Re_find_cpu = re.compile("Cpu\(s\)\:\s*(\d+\.\d+)\sus\,  (\d+\.\d+) sy\,  (\d+\.\d+) ni\, (\d+\.\d+) id\,\s*(\d+\.\d+) wa\,\s+(\d+\.\d+)\shi\,\s*(\d+\.\d+)\s*si\,\s*(\d+\.\d+)\sst")
    Re_find_mem = re.compile("KiB\sMem\s\:\s+(\d+)\stotal\,\s+(\d+)\sfree\,\s+(\d+)\sused\,\s+(\d+)\sbuff\/cache")
    Re_find_cahce_mem = re.compile("KiB\sSwap\:\s+(\d+)\stotal\,\s+(\d+)\s+free\,\s+(\d+)\s+used\.\s+(\d+)\savail\sMem ")
    result = Popen(["top -bi -n 1"], shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    content = result.stdout.read()
    # print(type(content))
    content = content.decode("utf-8")
    # print(type(content))
    # print(content)

    loadaverge_info = Re_find_loadaverge.findall(content)
    task_info = Re_find_task.findall(content)
    cpu_info = Re_find_cpu.findall(content)
    men_info = Re_find_mem.findall(content)
    chache_info = Re_find_cahce_mem.findall(content)

    # print(loadaverge_info)
    # print(task_info)
    # print(cpu_info)
    # print(men_info)
    # print(chache_info)
    b = time.time()
    # print(b-a)

    system_info = {
        "loadaverge_info": loadaverge_info[0],
        "task_info": task_info[0],
        "cpu_info": cpu_info[0],
        "men_info": men_info[0],
        "chache_info": chache_info[0]
    }
    return system_info
    # return content.decode("utf-8")





@app.route("/")
def index():
    return render_template("scrapyd_home.html")


twistedapp = Twisted(app)
if __name__ == '__main__':
    twistedapp.run(port=5001)
    # print(getCPU_info())
    # data = getCPU_info()
    # datalist = data.split('\n\n')
    # for onedata in datalist:
    #     print(onedata)
    #     print("------------!!!-------------")
    # print(data)
