from ult.ClientAct import *
from ult.killThread import *
import sys
import time


def usage():
    print('Usage: ')
    print('    python client.py [--mode]')
    print('Mode list:')
    print('  -p, --purchse')
    print('  -r, --run')

def exceptionProcess():
    try:
        stopThread(checkAliveThread)
    except ValueError as e:
        print(e)
        sys.exit(-1)
    except SystemError as e:
        print(e)
        sys.exit(-1)

if __name__ == "__main__":
    if (len(sys.argv) != 2):
        print("Parameter error")
        usage()
        sys.exit(-1)

    Req = sys.argv[1]
    if (Req == '-p' or Req == '--purchase'):
        try:
            purchaseLicense()
        except KeyboardInterrupt:
            print('KeyboardInterrupt...')
            pass
        except TimeoutError:
            pass
        sys.exit(0)

    err = ''
    if (Req == '-r' or Req=='--run'):
        try:
            err = requestTicket()
        except TimeoutError:
            sys.exit(-1)
    else:
        usage()
        sys.exit(-1)

    if err != '':
        print('Could not get ticket: ', err)
        sys.exit(0)
    try:
        checkAliveThread=CheckAliveThread()
        checkAliveThread.start()
        print('Now start working...')
        print('--------------------')
        while True:
            str = ''
            str = input()
            print(str)
            if str == 'exit':
                break
            if checkAliveThread.refused==True:
                raise RefusedError
        print('--------------------')
        print('Done, now release the license...')
    except TimeoutError:
        exceptionProcess()
    except KeyboardInterrupt:
        print('KeyboardInterrupt...')
        pass
    except RefusedError as e:
        print('Refused by the server...')
        exceptionProcess()

    exceptionProcess()
    if releaseTicket():
        print('Released ticket, now exit.')
    else:
        print('Cannot released ticket, now exit.')
    sys.exit(0)