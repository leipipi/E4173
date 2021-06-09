from ult.config import *
from ult.killThread import *
from socket import *
from random import randint
import os
import re
import sys
import sqlite3
import time
import platform
import threading
import schedule


Tickets = {}
madeTickets = False


class DjangoThread(threading.Thread):
    def run(self):
        try:
            os.system("manage runserver")
        except KeyboardInterrupt:
            print('DjangoThread KeyboardInterrupt...')
            os._exit(-1)

class ReclaimThread(threading.Thread):
    def run(self):
        schedule.every(30).seconds.do(checkReclaim)
        while True:
            try:
                schedule.run_pending()
            except KeyboardInterrupt:
                print('KeyboardInterrupt...')
                print('DjangoThread KeyboardInterrupt...')
                os._exit(-1)

def makeTicket():
    ticket = ''
    for i in range(0, lenTicket):
        ticket += str(randint(0, 9))

    return ticket


def makeLicense():
    license = ''
    for i in range(0, lenLicense):
        license += str(randint(0, 9))

    return license


def checkReclaim():
    print('>检查声明信息:')
    conn = sqlite3.connect(databaseName)
    curs = conn.cursor()
    sql = "select * from client"
    curs.execute(sql)
    conn.commit()
    res = curs.fetchall()
    print(res)
    for line in res:
        latestTime=time.strptime(line[1],'%Y/%m/%d %H:%M:%S')
        if time.time()-time.mktime(latestTime)>30:
            print('delete: Tno=',line[0],', latestTime=',line[1],', lno=',line[2])
            sql = "delete from client where Tno='{}' and latestTime='{}'".format(line[0],line[1])
            print(sql)
            curs.execute(sql)
            conn.commit()
    return


def getUserNum(license):
    conn = sqlite3.connect(databaseName)
    curs = conn.cursor()
    sql = "select count(*) from client where lno = '{}'".format(license)
    curs.execute(sql)
    userNum = curs.fetchall()[0][0]
    curs.close()
    conn.close()
    return userNum


def getMaxNum(license):
    conn = sqlite3.connect(databaseName)
    curs = conn.cursor()
    sql = "select userNum from license where lno = '{}'".format(license)
    curs.execute(sql)
    res = curs.fetchall()
    print(res, 'len=', len(res))
    if len(res) == 0:
        return
    maxNum = res[0][0]
    print('maxNum=', maxNum)
    curs.close()
    conn.close()
    return maxNum


def searchTicket(ticket, license):
    conn = sqlite3.connect(databaseName)
    curs = conn.cursor()
    exist = 0
    sql = "select count(*) from client where Tno = '{0}' and Lno = '{1}'".format(
        ticket, license)
    try:
        curs.execute(sql)
        exist = curs.fetchall()[0][0]
    except sqlite3.OperationalError as msg:
        print(msg)
    if exist == 1:
        return True
    return False

def searchLicense(license):
    conn = sqlite3.connect(databaseName)
    curs = conn.cursor()
    exist = 0
    sql = "select count(*) from license where Lno = '{0}'".format(license)
    try:
        curs.execute(sql)
        exist = curs.fetchall()[0][0]
    except sqlite3.OperationalError as msg:
        print(msg)
    if exist == 1:
        return True
    return False

def requestTicket(license):
    userNum = getUserNum(license)

    maxNum = getMaxNum(license)

    if (userNum < maxNum):
        conn = sqlite3.connect(databaseName)
        curs = conn.cursor()
        sql = 'insert into client(Tno,latestTime,Lno) values (:Tno,:latestTime,:Lno)'
        param = []
        ticket = makeTicket()
        while searchTicket(ticket, license) == True:
            ticket = makeTicket()
        param.append(ticket)
        param.append(
            time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(time.time())))
        param.append(license)
        try:
            curs.execute(sql, param)

        except sqlite3.OperationalError as msg:
            print(msg)
            return ""

        conn.commit()
        curs.close()
        conn.close()
        return ticket

    return ''


def releaseTicket(ticket, license):
    conn = sqlite3.connect(databaseName)
    curs = conn.cursor()
    if searchTicket(ticket,license)==False:
        return False
    sql = "delete from client where lno = '{}' and tno = '{}'".format(
        license, ticket)
    curs.execute(sql)
    conn.commit()
    return True


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
    conn = sqlite3.connect(databaseName)
    curs = conn.cursor()
    latestTime = time.strftime('%Y/%m/%d %H:%M:%S',
                               time.localtime(time.time()))
    sql = "update client set latesttime='{}' where lno = {} and tno = {}".format(
        latestTime, license, ticket)
    curs.execute(sql)
    conn.commit()
    result = curs.fetchall()
    print(result)
    sendM = 'GOOD:'
    return sendM



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


def doPURC(info):
    license = makeLicense()
    while searchLicense(license) == True:
        license = makeLicense()
    infos = info.split(':')
    userName = infos[1]
    password = infos[2]
    userNum = int(infos[3])
    conn = sqlite3.connect(databaseName)
    curs = conn.cursor()
    sql = 'insert into license(Lno,userName,password,userNum) values (:license,:userName,:password,:userNum)'
    param = []
    param.append(license)
    param.append(userName)
    param.append(password)
    param.append(userNum)
    try:
        curs.execute(sql, param)
    except sqlite3.OperationalError as msg:
        print(msg)
        sendM = "FAIL:Insert error"
        return sendM
    print("License generated successfully")
    sendM = "PERM:" + license
    conn.commit()
    return sendM


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


def initDB():
    conn = sqlite3.connect(databaseName)
    curs = conn.cursor()
    try:
        sql = "select * from license"
        curs.execute(sql)
        print('Table LICENSE has been created')
    except sqlite3.OperationalError:
        sql = "create table license(Lno char(10) primary key,userName char(20),password char(20),userNum int)"
        print('Create table license...')
        curs.execute(sql)

    try:
        sql = "select * from client"
        curs.execute(sql)
        print('Table CLIENT has been created')

    except sqlite3.OperationalError:
        sql = "create table client(Tno char(20),latestTime char(20),Lno char(20),primary key(Tno,Lno))"
        print('Create table client...')
        curs.execute(sql)

    conn.commit()
    return