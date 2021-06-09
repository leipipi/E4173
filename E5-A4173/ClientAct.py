from ult.config import *
from socket import *
import os
import threading, traceback, sys
import schedule
import time

ticket = ''
license = ''


class CheckAliveThread(threading.Thread) :
    def __init__(self) :
        super(CheckAliveThread, self).__init__()
        self.refused = False

    def run(self) :
        schedule.every(5).seconds.do(checkAlive)
        try :
            while True :
                schedule.run_pending()
                self.refused = False
        except RefusedError as e :
            self.refused = True


def purchaseLicense() :
    sock = socket(AF_INET, SOCK_DGRAM)

    reqTimes = 3
    while reqTimes :
        reqTimes -= 1

        try :
            userName = input("请输入用户名:")
            if (userName == "") :
                print("用户名不能为空")
                continue
            password = input("请输入密码:")
            if (password == "") :
                print("密码不能为空")
                continue
            userNum = input("请输入用户数:")
            if (userNum == "") :
                print("用户数不能为空")
                continue
            try :
                int(userNum)
            except Exception as ex :
                print("用户数需要为整数")
                continue

            msg = 'PURC:' + userName + ':' + password + ':' + userNum
            sock.sendto(msg.encode(), ServerIP_Port)
            sock.settimeout(5)
            try :
                info = sock.recv(MSGLEN).decode()
            except OSError as e :
                print(e)
                raise TimeoutError
            check = info[:4]

            if check == 'PERM' :
                print("购买成功")
                print("许可证编号是:" + info[5 :])
                sock.close()
                return True
            elif check == 'FAIL' :
                print("购买失败")
            else :
                print('未知信息:', info)
                sock.close()
                return False
            break
        except ConnectionError as Err :
            print('连接错误', Err)
            continue
    print("购买失败: 无法从服务端获得许可证!")
    sock.close()
    return False


def requestTicket() :
    Verified = False
    global license
    filename = "license.lic"
    if (os.path.isfile("license.lic") == True) :
        Verified = True
        with open(filename, "r") as reader :
            license = reader.readline()

    else :
        license = input("Please enter a license:")

    sock = socket(AF_INET, SOCK_DGRAM)
    connected = False
    reqTimes = 3
    check = ''
    while reqTimes :
        reqTimes -= 1

        try :
            msg = 'HELO:' + license
            sock.sendto(msg.encode(), ServerIP_Port)
            sock.settimeout(5)
            try :
                info = sock.recv(MSGLEN).decode()
            except OSError as e :
                print(e)
                raise TimeoutError
            check = info[:4]

            if check != 'WELC' and check != 'RFUS' :
                print('错误:', info)
                sock.close()
                return 'Unknown'
            connected = True
            break

        except ConnectionError as Err :
            print('连接错误', Err)
            continue

    sock.close()
    if connected == False :
        return '连接服务端失败'

    if check == 'RFUS' :
        return info[5 :]

    if (check == 'WELC') and Verified == False :
        with open(filename, "w") as writer :
            writer.write(license)

    global ticket
    ticket = info[5 :]
    return ''


def checkAlive() :
    print('\n------\n检测许可证状态...')
    sock = socket(AF_INET, SOCK_DGRAM)
    ans = ''
    checkTimes = 3
    while checkTimes :
        checkTimes -= 1
        try :
            msg = 'CKAL:' + license + ticket
            print("msg :", msg)
            sock.sendto(msg.encode(), ServerIP_Port)
            sock.settimeout(5)
            try :
                info = sock.recv(MSGLEN).decode()
            except OSError as e :
                print('超时错误', e)
                print('请重试... (剩余时间: ' + str(checkTimes) + ')')
                continue
            ans = info[:4]
            break
        except ConnectionError as Err :
            print('请重试... (剩余时间: ' + str(checkTimes) + ')')
            continue

    sock.close()
    print('------')
    if ans == 'RFUS' :
        raise RefusedError
    return ans == 'GOOD'


def releaseTicket() :
    print('归还票据...')
    sock = socket(AF_INET, SOCK_DGRAM)
    info = ''
    relsTimes = 3
    while relsTimes :
        relsTimes -= 1

        try :
            msg = 'RELS:' + license + ticket
            print("msg : " + msg)
            sock.sendto(msg.encode(), ServerIP_Port)
            sock.settimeout(5)
            try :
                info = sock.recv(MSGLEN).decode()
            except OSError as e :
                print('超时错误', e)
                print('请重试... (剩余时间: ' + str(relsTimes) + ')')
                continue
            break
        except ConnectionError as Err :
            print('连接错误', Err)
            print('请重试... (剩余时间: ' + str(relsTimes) + ')')
            continue

    sock.close()
    return info[:4] == 'GBYE'
