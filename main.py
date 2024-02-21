import os
import sys
import requests
import json
import time
import datetime
import streamlink
import platform
import subprocess


def console_print(message):
    time = datetime.datetime.today().strftime('%Y-%m-%dT%H-%M-%S')
    print("[{}] {}".format(time, message))


USER_NAME = None
USER_PASSWORD = None

if "USER_NAME" in os.environ.keys() and "USER_PASSWORD" in os.environ.keys():
    USER_NAME = os.environ["USER_NAME"]
    USER_PASSWORD = os.environ["USER_PASSWORD"]
else:
    try:
        with open("config.json") as fp:
            user_config = json.load(fp)
            USER_NAME = user_config["USER_NAME"]
            USER_PASSWORD = user_config["USER_PASSWORD"]
    except FileNotFoundError:
        console_print("""Environment variables are not set, and config.json does not exist.
        Set environment variable[USER_NAME, USER_PASSWORD] or create config.json from config-sample.json
                      """)
        exit(-1)
    except IOError as e:
        console_print("IO Error occurred while reading config.json. please check your file")
        console_print("[Cause] : {e}".format(e=e))
        exit(-1)
    except Exception as e:
        console_print("Unknown Error occurred while reading config.json. please check your file")
        console_print("[Cause] : {e}".format(e=e))
        exit(-1)


RETRY_INTERVAL = int(os.getenv("RETRY_INTERVAL", 60))

cookie_dict = None


def id_or_login_detect(value):
    return value.isnumeric()


def get_id_from_login(user_login):
    get_cookie()
    url = f'https://live.afreecatv.com/afreeca/player_live_api.php?bid={user_login}'
    data = {
        'bid': user_login,
        'type': 'live'
    }
    req = requests.post(url, data=data, cookies=cookie_dict)
    result = req.json()
    return result['CHANNEL']['BNO']


def get_login_from_id(user_id):
    get_cookie()
    url = f'https://live.afreecatv.com/afreeca/player_live_api.php?bno={user_id}'
    data = {
        'bno': user_id,
        'type': 'live'
    }
    req = requests.post(url, data=data, cookies=cookie_dict)
    result = req.json()
    return result['CHANNEL']['BJID']


def get_cookie():
    global cookie_dict
    url = "https://login.afreecatv.com/app/LoginAction.php"
    data = {
        "szWork": "login",
        "szType": "json",
        "szUid": USER_NAME,
        "szPassword": USER_PASSWORD,
        "isSaveId": "true",
        "isSavePw": "false",
        "isSaveJoin": "false",
        "isLoginRetain": "Y"
    }

    req = requests.post(url, data=data)
    cookies = req.cookies
    cookie_dict = requests.utils.dict_from_cookiejar(cookies)


def stream_detect(user_id):
    url = f'https://live.afreecatv.com/afreeca/player_live_api.php'
    data = {
        'bno': user_id,
        'type': 'live'
    }

    req = requests.post(url, data=data)
    result = json.loads(req.text)

    if 'RESOLUTION' in result['CHANNEL']:
        return True
    else:
        return False


def get_stream_m3u8_streamlink(user_login):
    stream_url = "play.afreecatv.com/" + user_login
    streams = streamlink.streams(stream_url)
    
    list = {}
    for key, value in streams.items():
        list[key] = value.url

    return list


def get_stream_m3u8_direct(user_id):
    url = 'https://live.afreecatv.com/afreeca/player_live_api.php'
    data = {
        "bid": user_id,
        "quality": "original",
        "type": "aid",
        "pwd": "",
        "stream_type": "common",
    }

    req = requests.post(url, data=data, cookies=cookie_dict)
    result = req.json()

    if result['CHANNEL']['RESULT'] == 0:
        # 방송중이 아님
        return None
    elif result['CHANNEL']['RESULT'] == 1:
        # 방송중
        m3u8_url = "https://live-global-cdn-v02.afreecatv.com/live-stm-16/auth_playlist.m3u8?aid=" + result['CHANNEL']['AID']
        return m3u8_url
    elif result['CHANNEL']['RESULT'] == -6:
        # 로그인 필요
        get_cookie()
        return get_stream_m3u8_direct(user_id)
    else:
        # 알 수 없는 오류
        return None


def basic_file_info(user_login, extension):
    date = datetime.datetime.today().strftime('%Y-%m-%dT%H-%M-%S')
    path = './' + user_login + '/' + date + '.' + extension
    return path


def download_stream_m3u8_legacy(user_login, m3u8_url, extension):
    path = basic_file_info(user_login, extension)

    if platform.system() == "Windows":
        CREATE_NO_WINDOW = 0x08000000
        subprocess.run(
            ["streamlink", "--stream-segment-threads", "5", "--stream-segment-attempts", "5", "--hls-live-restart",
             "--afreeca-username", USER_NAME, "--afreeca-password", USER_PASSWORD, m3u8_url, "best", "--stream-segment-losscheck",
             path, "-o", path], creationflags=CREATE_NO_WINDOW)
    else:
        subprocess.run(
            ["streamlink", "--stream-segment-threads", "5", "--stream-segment-attempts", "5", "--hls-live-restart",
             "--afreeca-username", USER_NAME, "--afreeca-password", USER_PASSWORD, m3u8_url, "best",
             "--stream-segment-losscheck",
             path, "-o", path])#, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return


def download_stream_legay(user_login, extension):
    path = basic_file_info(user_login, extension)
    stream_url = 'https://play.afreecatv.com/' + user_login

    if platform.system() == "Windows":
        CREATE_NO_WINDOW = 0x08000000
        subprocess.run(["streamlink", stream_url, "best", "-o", path, "--afreeca-username", USER_NAME, "--afreeca-password", USER_PASSWORD, "--afreeca-purge-credentials"], creationflags=CREATE_NO_WINDOW)
    else:
        subprocess.run(["streamlink", stream_url, "best", "-o", path, "--afreeca-username", USER_NAME, "--afreeca-password", USER_PASSWORD, "--afreeca-purge-credentials"])
    return


console_print("Program started")

try:
    user_info_list = sys.argv[1:]
except:
    console_print("Please input user login")
    exit()

if len(user_info_list) == 0:
    user_info = input("Input streamer nickname(if you want to exit, press enter): ")
    if user_info == "":
        exit()

if len(user_info_list) > 1:
    console_print("only one streamer nickname is allowed")
    exit()

user_info = user_info_list[0]

# if id_or_login_detect(user_info):
#     user_id = user_info
#     user_login = get_login_from_id(user_id)
# else:
#     user_login = user_info
#     user_id = get_id_from_login(user_login)

user_login = user_info

repeat_check = True
latest_error = ""

if not os.path.exists("{}".format(user_login)):
    os.makedirs("{}".format(user_login))

while True:
    try:
        if repeat_check:
            console_print("[{user_login}] Waiting to start streaming".format(user_login=user_login))
            repeat_check = False
        
        stream_m3u8 = get_stream_m3u8_direct(user_login)
        if stream_m3u8 is not None:
            console_print("[{user_login}] Stream started".format(user_login=user_login))
            try:
                download_stream_m3u8_legacy(user_login, stream_m3u8, "ts")
            except Exception as e:
                print("Error: {}".format(e))
                continue

            console_print("[{user_login}] Stream ended".format(user_login=user_login))
            repeat_check = True

    except Exception as e:
        if latest_error != e or 1==1:
            console_print("Error: {}".format(e))
            latest_error = e

    time.sleep(RETRY_INTERVAL)
