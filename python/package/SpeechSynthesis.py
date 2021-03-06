# -*- coding: utf-8 -*-
# @Date: 2019-12-29 13:34:16
# @LastEditTime: 2020-03-09 00:15:03
# @Description: 语音合成类，可以增加多家产品,暂实现百度语音识别

from MsgProcess import MsgProcess, MsgType
from python.package.CacheFileManager import CacheFileManager
from hashlib import md5
import os
import logging

class SpeechSynthesis(MsgProcess):
    '''语音合成类'''

    def __init__(self, msgQueue):
        super().__init__(msgQueue)

        if self.config['ApiConfig']['SpeechSynthesis'] == 'Baidu':
            from module.SpeechSynthesis.baidu import baidu

            sps = baidu(self.CUID)
            self.SpeechSynthesis = sps.main


        if self.config['ApiConfig']['SpeechSynthesis'] == 'Xunfei':
            from module.SpeechSynthesis.xunfei import xunfei

            sps = xunfei(self.CUID)
            self.SpeechSynthesis = sps.main

    # 开始合成，由接口类重写这个方法
    def SpeechSynthesis(self, text, fileName):
        pass

    def Text(self, message):
        text = message['Data']
        if text and isinstance(text, str) and len(text) < 1024:
            logging.info('[%s] request Speech: %s' %(message['Sender'],text))
            name = md5(text.encode('utf-8')).hexdigest() + r'.mp3'
            CachePath = r'runtime/soundCache'
            fileName = os.path.join(CachePath, name)
            if os.path.exists(fileName):
                #判断文件是否为0kb
                if not "0" in os.popen("du -sh "+fileName).read()[0]:
                    logging.debug('本地墦放')
                    self.playSound(fileName)
                    return 1

            fileName = self.SpeechSynthesis(text, fileName)
            if fileName:
                logging.debug('网络墦放')
                self.playSound(fileName)
        # self.send(MsgType=MsgType.JobsDone, Receiver = message['Sender'])

    def playSound(self, fileName):
        '''播放音乐文件fileName 可能会实现一个player类 暂用mpg123 '''
        CacheFileManager.add(fileName)
        logging.debug('墦放 %s ' % fileName)
        os.system("mpg123  -q  {} ".format(fileName))
        # os.popen("sudo mpg123  -q  {}".format(fileName))
        # os.popen("sudo aplay -q {}".format(fileName))
