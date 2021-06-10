from random import randint
import re
import sys
import time
from socket import *
import inspect
import ctypes

Tickets = {}
madeTickets = False
MSGLEN = 128

ServerIP_Port = ('127.0.0.1', 10000)

lenTicket = 10

lenLicense = 10


#创建票据
def makeTicket():
    ticket = ''
    for i in range(0, lenTicket):
        ticket += str(randint(0, 9))

    return ticket
#创建证书
def makeLicense():
    license = ''
    for i in range(0, lenLicense):
        license += str(randint(0, 9))

    return license

#检查声明
def checkReclaim():
    res = curs.fetchall()
    print(res)
    for line in res:
        latestTime=time.strptime(line[1],'%Y/%m/%d %H:%M:%S')
    return

#获取用户数量
def getUserNum(license):
    userNum = curs.fetchall()[0][0]
    return userNum

#获取最大用户数
def getMaxNum(license):
    res = curs.fetchall()
    print(res, 'len=', len(res))
    if len(res) == 0:
        return
    maxNum = res[0][0]
    print('maxNum=', maxNum)
    return maxNum


#建立线程
def _async_raise(tid, exctype) :
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype) :
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0 :
        raise ValueError("invalid thread id")
    elif res != 1 :
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")

#停止线程
def stopThread(thread) :
    _async_raise(thread.ident, SystemExit)

#寻找票据
def searchTicket(ticket, license):
    exist = 0
    if exist == 1:
        return True
    return False
def requestTicket(license):
    userNum = getUserNum(license)

    maxNum = getMaxNum(license)

    if (userNum < maxNum):
        param = []
        ticket = makeTicket()
        while searchTicket(ticket, license) == True:
            ticket = makeTicket()
        param.append(ticket)
        param.append(
            time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(time.time())))
        param.append(license)


        return ticket

    return ''

#释放票据
def releaseTicket(ticket, license):
    if searchTicket(ticket,license)==False:
        return False
    return True

#向客户端回应
def doHELO(info):
    req = re.findall('\d{10}', info)
    sendM = ''

    if req == []:
        print('>Requst Unknown')
        sendM = 'RFUS:Cannot recognize your request'
    else:
        license = req[0]

        if searchLicense(license) == False:
            print('>License error...')
            sendM = 'RFUS:License error'
            return sendM

        ticket = requestTicket(license)
        if ticket:
            print(
                '>Deliver ticket:', ticket,
                '(rest:' + str(getMaxNum(license) - getUserNum(license)) + ')')
            sendM = 'WELC:' + ticket
        else:
            print('>NO ticket chance remain...')
            sendM = 'RFUS:No ticket rest'

    return sendM

#检查生存期
def doCKAL(info):
    rels = re.findall('\d{20}', info)
    sendM = ''

    if rels == []:
        print('>Requst Unknown')
        sendM = 'UKNW:Cannot recognize your request'
    else:
        license = rels[0][0:10]
        ticket = rels[0][10:]
    if searchTicket(ticket,license)==False:
        return 'RFUS: Failed to update'
    latestTime = time.strftime('%Y/%m/%d %H:%M:%S',
                               time.localtime(time.time()))
    result = curs.fetchall()
    print(result)
    sendM = 'GOOD:'
    return sendM


#释放票据
def doRELS(info):
    rels = re.findall('\d{20}', info)
    sendM = ''

    if rels == []:
        print('>Requst Unknown')
        sendM = 'UKNW:Cannot recognize your request'
    else:
        license = rels[0][0:10]
        ticket = rels[0][10:]

        if searchTicket(ticket, license) == False:
            print('>>WARNING<< someone try to release an unused ticket!!')
            sendM = 'WARN:!!!'

        elif searchTicket(ticket, license) == True:
            releaseTicket(ticket, license)
            print(">Release ticket")
            sendM = 'GBYE:Thank you for your using'

    return sendM

#创建用户证书
def doPURC(info):
    license = makeLicense()
    while searchLicense(license) == True:
        license = makeLicense()
    infos = info.split(':')
    userName = infos[1]
    password = infos[2]
    userNum = int(infos[3])
    param = []
    param.append(license)
    param.append(userName)
    param.append(password)
    param.append(userNum)
    print("证书创建成功")
    sendM = "PERM:" + license
    conn.commit()
    return sendM

#处理任务
def handleRequest(sock, info, addr):
    info = info.decode()
    check = info[:4]
    sendM = ''


    if check == 'HELO':
        print('-Request Ticket with License:', info, 'from: ', addr)
        sendM = doHELO(info)

    elif check == 'CKAL':
        print('-Request for checking', info, 'from: ', addr)
        sendM = doCKAL(info)

    elif check == 'RELS':
        print('-Request for releasing:', info, 'from: ', addr)
        sendM = doRELS(info)

    elif check == 'PURC':
        print("Generate license...")
        sendM = doPURC(info)
    else:
        print('-Request Unrecognized:', info, 'from: ', addr)
        sendM = 'UKNW:???'

    sock.sendto(sendM.encode(), addr)
    return


if __name__ == "__main__":
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(('0.0.0.0', 10000))

    try:
        djangoThread=DjangoThread()
        djangoThread.start()
        reclaimThread=ReclaimThread()
        reclaimThread.start()
        while True:
            print('等待下个请求...')#开启线程，等待客户端请求
            info, addr = sock.recvfrom(MSGLEN)
            handleRequest(sock, info, addr)
    except KeyboardInterrupt:
        try:
            stopThread(reclaimThread)
            stopThread(djangoThread)
        except ValueError as e:
            print(e)
            sock.close()
            sys.exit(-1)
        except SystemError as e:
            print(e)
            sock.close()
            sys.exit(-1)
    sock.close()