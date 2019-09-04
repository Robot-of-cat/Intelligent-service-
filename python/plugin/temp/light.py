import os,time
import RPi.GPIO as GPIO
from plugin import Plugin
from package.config import config           #导入固件配置

class Light(Plugin):
    '''灯控制类'''
    def __init__(self, public_obj):
        #设置不显示警告
        GPIO.setwarnings(False)

        #设置读取面板针脚模式
        GPIO.setmode(GPIO.BOARD)

        self.pin_deng_kg   = config['GPIO']['deng_kg']               # 设置灯控制脚
        GPIO.setup(self.pin_deng_kg,GPIO.OUT)

    '''
    开关灯（硬件开关）
    isst - 1 / 0 ： 开 / 关
    '''
    def openclose_light(self, isst = 1):
        light_sw = GPIO.input(self.pin_deng_kg)

        if isst == 1:
            if int(light_sw) != 1:
                GPIO.output(self.pin_deng_kg,GPIO.HIGH)

        elif isst == 0:
            if int(light_sw) != 0:
                GPIO.output(self.pin_deng_kg,GPIO.LOW)

    def main(self,txt):
        if txt == "off":
            self.openclose_light(0)
            return {'state':True,'data': "灯已关闭",'msg':'操作成功！'}
        elif txt == 'on':
            self.openclose_light(1)
            return {'state':True,'data': "灯已打开",'msg':'操作成功！'}

    #灯当前状态
    def init_light(self):
        light_sw = GPIO.input(self.pin_deng_kg)
        return str( light_sw )

    # 打开灯
    def start(self,name):
        if name['action'] == 'open':
            return self.main("on")
        else:
            return self.main("off")