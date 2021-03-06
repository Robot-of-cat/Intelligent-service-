# -*- coding: utf-8 -*-
# @Author: drbdrb,
# @Date: 2019-09-16 10:42:36
# @LastEditTime: 2020-03-19 09:55:12
# @Description: 设备类插件

import json
import logging
import math
import os
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import RPi.GPIO as GPIO
from MsgProcess import MsgProcess, MsgType
from python.module.WebApi.hefeng import hefeng

# 旋转屏幕数值对应表
rotate_array = {
    "0": "不旋转",
    "1": "旋转90度",
    "2": "旋转180度",
    "3": "旋转270度",
    "0x10000": "左右翻转",
    "0x20000": "上下翻转"
}

class Volume:
    @staticmethod
    def isWm8960(self):
        cmd = 'lsmod | grep -i snd_soc_wm8960_soundcard'
        cmd_ret = os.popen(cmd).read()

        restr = r'snd_soc_wm8960_soundcard\s+\d+\s+(\d)'
        math = re.search(restr, cmd_ret,  re.M | re.I)
        if math:
            if int(math.group(1)) <= 6:
                return False
            else:
                return True
        return True

    @staticmethod
    def get():
        ''' 取得音量大小 '''
        info = os.popen("sudo amixer sget Speaker").read()
        patten = r'Front\sLeft:\sPlayback\s(\d+)\s\[(\d+)\%\]'
        varStr = re.search(patten, info, re.M | re.I)
        if varStr:
            realvol = int(varStr.group(2))
        else:
            realvol = 80
        vol = int(1.7972 * math.pow(2.718, 0.04 * realvol))
        return vol

    # 设置音量
    @staticmethod
    def set(val=60):
        ''' 设置音量 '''
        val = 24.979 * math.log(val) - 14.581
        os.system("sudo amixer sset Speaker {}% ".format(val))

    @staticmethod
    def add():
        Volume.set(Volume.get() + 10)

    @staticmethod
    def sub():
        Volume.set(Volume.get() - 10)


class Screen():
    '''屏幕控制类'''

    @staticmethod
    def setPower(val=1):
        '''设置开关屏幕'''
        os.system('sudo vcgencmd display_power ' + str(val))

    @staticmethod
    def getPower():
        ''' 获取屏幕开关状态 '''
        st = os.popen('sudo vcgencmd display_power').read()
        starr = st.strip().split('=')
        return str(starr[1])

    @staticmethod
    def getRotate():
        ''' 屏幕旋转状态 '''
        if "Pi 4" in os.popen("cat /proc/device-tree/model").read():
            config = '/etc/profile.d/hdmi.sh'
            if os.path.exists(config):
                with open(config, "r") as f:
                    fstr = f.read()
                if "left" in fstr :
                    return 1
                if "right" in fstr:
                    return 2
                if "inverted" in fstr:
                    return 3
            return 0

        else:
            config = '/boot/config.txt'
            f = open(config, "r")
            fstr = f.read()
            f.close()
            restr = r'^display_rotate\s*=\s*(\d)'
            rotate_val = 0
            rema = re.search(restr, fstr, re.M | re.I)
            if rema:
                rotate_val = rema.group(1)
            return rotate_val


    @staticmethod
    def setRotate(val=0):
        """ 设置屏幕旋转 """

        if "Pi 4" in os.popen("cat /proc/device-tree/model").read():

            ''' 旋转屏幕 val 度 '''
            config = '/etc/profile.d/hdmi.sh'
            if not os.path.exists(config):
                os.system("sudo touch "+config)
                os.system("sudo chmod 777 "+config)
            direction = ("xrandr -o normal","xrandr -o left","xrandr -o right","xrandr -o inverted")
            val=int(val)
            if val<4:
                with open(config, "w") as f:
                    f.write(direction[val])
                    os.system(direction[val])
            return

        else:

            config = '/boot/config.txt'
            f = open(config, "r")
            fstr = f.read()
            f.close()

            restr = r'^display_rotate\s*=\s*(\d)'
            rema = re.search(restr, fstr, re.M | re.I)
            new_api = 'display_rotate=' + str(val)
            if rema:
                cmd = "sudo sed -i s/^display_rotate\s*=\s*[0-9]*/'"+ new_api +"'/g "+ config
            else:
                appstr = "\n" + str(new_api) + "\n"
                cmd = "sudo sh -c 'echo \""+ appstr +"\" >> "+ config +"'"

            os.system(cmd)
            os.system('sudo reboot')


def get_ip_address():
    ''' 取IP和对应的网卡 仅在树莓派上能运行 '''
    re_json = list()
    restr = r'inet\s+([\d+\.]+)\s+'
    eth0ip = os.popen('ifconfig eth0').read()
    matc = re.search(restr, eth0ip, re.M | re.I)
    if matc:
        ethjson = {
            'devname': 'eth0',
            'name': '有线网卡',
            'ip': str(matc.group(1))
        }
        re_json.append(ethjson)

    wlanip = os.popen('ifconfig wlan0').read()
    matc = re.search(restr, wlanip, re.M | re.I)
    if matc:
        ethjson = {
            'devname': 'wlan0',
            'name': '无线网卡',
            'ip': str(matc.group(1))
        }
        re_json.append(ethjson)
    return re_json

def process(name):
    taskcmd = 'ps ax | grep '+name
    out = os.popen(taskcmd).read()
    pat = re.compile(r'(\d+).+({0})'.format( name))
    return pat.findall(out)

def SoundCardIsPlay():
    ''' 声卡是否在播放   是则返回True 否则返回False '''
    #cmd = 'cat /proc/asound/wm8960soundcard/pcm0p/sub0/status'
    #return "RUNNING" in os.popen(cmd).read()

    for x in ["mplay","mpg123","aplay"]:
        if len(process(x)) >=3:
            return 1
    return 0

class Device(MsgProcess):

    def __init__(self, msgQueue):
        super().__init__(msgQueue)
        self.pin_detect_man = 16         # 人体探测（引脚定义）
        self.powersavetime = 0           # (屏幕)节能时间,持续n分钟都没有人,则关闭屏幕节能.可选数值[1~65536] 如果为0 则关闭此功能

    def detect_man(self):
        ''' 人体探测 '''
        if self.pin_detect_man > 0:
            detect_val = GPIO.input(self.pin_detect_man)
            if detect_val>0:
                now_time = int(time.time())
                with open('runtime/detectval', 'w+' ) as f:
                    f.write( str(now_time) )

    def onoff_screen(self):
        '''开关屏幕'''
        if self.powersavetime > 0:
            with open('runtime/detectval', 'r') as f:
                val = f.read()
                if val:
                    if (time.time() - int(val)) >= self.powersavetime * 60:
                        on_staut = os.popen('sudo vcgencmd display_power').read()
                        starr = on_staut.strip().split('=')
                        if int(starr[1])==1:
                            os.system('sudo vcgencmd display_power 0 > /dev/null')
                    else:
                        on_staut = os.popen('sudo vcgencmd display_power').read()
                        starr = on_staut.strip().split('=')
                        if int(starr[1])==0:
                            os.system('sudo vcgencmd display_power 1 > /dev/null')

    def Text(self, message):
        Data = message['Data']
        if isinstance(Data, dict) and 'action' in Data.keys():
            self.mqttProcess(Data)
        elif isinstance(Data, str):
            self.worldsProcess(Data)
        self.Stop()  # 任务完成退出。

    def worldsProcess(self, Data):
        ''' 处理语言消息 '''
        Triggers = ["天气地址", "修改位置"]
        if any(map(lambda trig: trig in Data, Triggers)):
            res = Data[4:]
            if "天气地址修改为" in Data or "天气地址设置为" in Data:
                res = Data[7:]
            if "天气地址改为" in Data:
                res = Data[6:]
            if "修改位置为" in Data or  "天气地址是" in Data  or  "天气地址为" in Data:
                res = Data[5:]

            logging.debug(res)
            data = {'action': 'DEVICE_CITY', 'data': res}
            self.mqttProcess(data)
            return

        Triggers = ["打开屏幕", "打开显示"]
        if any(map(lambda trig: trig in Data, Triggers)):
            Screen.setPower(1)
            msg = '屏幕已经打开'
            self.say(msg)
            return

        Triggers = ["关闭屏幕", "关闭显示"]
        if any(map(lambda trig: trig in Data, Triggers)):
            Screen.setPower(0)
            msg = '屏幕已经关闭'
            self.say(msg)
            return

        Triggers = ["重启"]
        if any(map(lambda trig: trig in Data, Triggers)):
            msg = '好的，现在重启'
            self.say(msg)
            os.system("sudo reboot")
            return

        Triggers = ["关机"]
        if any(map(lambda trig: trig in Data, Triggers)):
            msg = '好的，正在关机'
            self.say(msg)
            os.system("sudo shutdown now")
            return

        Triggers = ["声音", "音量"]
        if any(map(lambda trig: trig in Data, Triggers)):

            secondTriggers = ['最大', '最强', '最响']
            if any(map(lambda trig: trig in Data, secondTriggers)):
                Volume.set(100)
                msg = '音量已设置为最大了'
                if not SoundCardIsPlay():
                    self.say(msg)
                return

            secondTriggers = ['最小', '最弱', '最低']
            if any(map(lambda trig: trig in Data, secondTriggers)):
                Volume.set(25)
                if not SoundCardIsPlay():
                    self.say('音量已设置为最小了')
                return

            secondTriggers = ["小一点", "小点", "小一些", "小1点", "小1些", "小些", "太大", "好大"]
            if any(map(lambda trig: trig in Data, secondTriggers)):
                value = (Volume.get() - 10) if Volume.get() >= 25 else 25
                Volume.set(value)
                if not SoundCardIsPlay():
                    self.say('音量已设置为{}'.format(value))
                return

            secondTriggers = ["大点", "大一点", "大一些", "大1点", "大1些", "大些", "太小", "好小"]
            if any(map(lambda trig: trig in Data, secondTriggers)):
                value = (Volume.get() + 10) if Volume.get() <= 90 else 100
                Volume.set(value)
                if not SoundCardIsPlay():
                    self.say('音量已设置为{}'.format(value))
                return

            number = re.findall(r'(\d+)', Data)
            if len(number) >= 1:
                number = number[0]
                try:
                    number = int(number)
                    value = number if number <= 100 else 100
                    value = number if number >= 25 else 25
                    Volume.set(value)
                    if not SoundCardIsPlay():
                        self.say('音量已设置为{}'.format(value))
                except Exception:
                    if not SoundCardIsPlay():
                        self.say("太难理解啦?")
                return

    def mqttProcess(self, Data):
        ''' 处理1.xx版本的mqtt消息  '''
        if Data['action'] == 'DEVICE_STATE':
            state = Data['state']
            if state == 'volume':  # 音量
                volume = str(Volume.get())
                mqtt = {"action": "DEVICE_STATE",
                        "info": {"code": "0000", "sound": volume}
                        }
                self.send(MsgType=MsgType.Text, Receiver="MqttProxy", Data=mqtt)

            elif state == 'screen':  # 屏幕状态
                screen = Screen.getPower()
                mqtt = {"action": "DEVICE_STATE",
                        "info": {"code": "0000", "screen": screen}
                        }
                self.send(MsgType=MsgType.Text, Receiver="MqttProxy", Data=mqtt)

            elif state == 'all':
                volume = str(Volume.get())
                screen = Screen.getPower()
                screenrotate = Screen.getRotate()
                ipAddrs = get_ip_address()
                city = self.config['LOCATION']
                weathcity = {'city': city['city'], 'city_cnid': city['city_cnid']}
                mqtt = {"action": "DEVICE_STATE",
                        "info": {
                            "sound": volume,
                            "screen": screen,
                            "screenrotate": screenrotate,
                            "devip": ipAddrs,
                            "weathcity": weathcity
                        }}
                self.send(MsgType=MsgType.Text, Receiver="MqttProxy", Data=mqtt)
                self.send(MsgType=MsgType.Text, Receiver="Screen", Data="微信小程序已连接")
                if not SoundCardIsPlay():
                    self.send(MsgType=MsgType.Text, Receiver="SpeechSynthesis", Data="微信小程序已连接")
            return

        elif Data['action'] == 'DEVICE_SCREEN':  # 开关屏幕
            value = Data['value']
            if value == 1 or value == '1':
                msg = '屏幕已经打开'
            else:
                msg = '屏幕已经关闭'
            mqtt = {'action': 'DEVICE_SCREEN',
                    'info': {"code": "0000", "msg": msg}}
            Screen.setPower(value)
            self.send(MsgType=MsgType.Text, Receiver="Screen", Data=msg)
            self.send(MsgType=MsgType.Text, Receiver="SpeechSynthesis", Data=msg)
            return

        elif Data['action'] == 'DEVICE_VOLUME':  # 设置音量
            value = int(Data['value'])
            Volume.set(value)
            msg = '音量已设置为{}%'.format(value)
            mqtt = {'action': 'DEVICE_VOLUME',
                    'info': {"code": "0000", "msg": value}}
            self.send(MsgType=MsgType.Text, Receiver="MqttProxy", Data=mqtt)
            self.send(MsgType=MsgType.Text, Receiver="Screen", Data=msg)
            if not SoundCardIsPlay():
                self.send(MsgType=MsgType.Text, Receiver="SpeechSynthesis", Data=msg)
            return

        elif Data['action'] == 'DEVICE_RTURN':  # 旋转屏幕
            value = Data['value']
            msg = '设置屏幕{}并重启生效'.format(rotate_array[str(value)])
            mqtt = {'action': 'DEVICE_RTURN','info': {"code": "0000", "msg": msg}}

            self.send(MsgType=MsgType.Text, Receiver="MqttProxy", Data=mqtt)
            self.send(MsgType=MsgType.Text, Receiver="Screen", Data=msg)
            self.send(MsgType=MsgType.Text, Receiver="SpeechSynthesis", Data=msg)
            time.sleep(1)
            Screen.setRotate(value)
            return

        elif Data['action'] == 'DEVICE_CITY':  # 修改天气城市
            data = Data['data']
            city = self.http_urllib(data)
            if city:
                self.config['LOCATION']['city'] = city['name']
                self.config['LOCATION']['city_cnid'] = city['id']
                self.saveConfig()

                msgJson = {'type': 'nav', 'data': {"event": "close"}}
                self.send(MsgType.Text, Receiver='Screen', Data=msgJson)
                self.send(MsgType.Text, Receiver='Screen', Data=msgJson)
                time.sleep(1)
                msg = "天气预报城市已修改为{}".format(city['name'])
                mqtt = {'action': 'DEVICE_CITY','info': {"code": "0000", "msg": msg}}
                self.send(MsgType=MsgType.Text, Receiver="MqttProxy", Data=mqtt)
                self.send(MsgType=MsgType.Text, Receiver="Screen", Data=msg)
                self.send(MsgType=MsgType.Text, Receiver="SpeechSynthesis", Data=msg)

            else:
                self.say("设置天气预报的地址失败，请说出城市名，比如:天气地址是北京")

        elif Data['action'] == 'DEVICE_WIFI':  # 设置WiFi网络
            import python.bin.Setnet as Setnet
            if isinstance(Data, dict) and 'wifiname' in Data.keys():
                Setnet.Wificore().config_wifi(Data)
                os.system('mpg123 -q '+ os.path.join("bin/setWifi/voice", '配网成功.mp3'))
                time.sleep(0.3)
                os.system("sudo reboot")
            if isinstance(Data, dict) and 'kill' in Data.keys():
                os.system('sudo ifconfig wlan0 down')
                os.system('sudo killall udhcpc')
                os.system('sudo killall wpa_supplicant')


    def http_urllib(self, postdata):
        heapi = hefeng()
        return heapi.getcityid(postdata)

    def Stop(self, message=None):
        # 保存音量信息
        os.system("alsactl --file data/conf/asound.state store ")
        super().Stop()
