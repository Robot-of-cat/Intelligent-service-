import pyaudio,time,webrtcvad,collections,sys,signal,wave,os,random,gc,re,threading
from array import array
from struct import pack
import multiprocessing as mp                            #多进程
from package.base import Base,log                       #基本类
import package.check as check                           #设备检测模块
import package.mymqtt as mymqtt                         #mqtt服务（神经网络）
import package.mysocket as mysocket                     #发送websocket
import package.include.snowboy.snowboy as snowboy       #语音唤醒
import package.include.yuyin as yuyin                   #语音相关操作（语音转文字：录音、识别）
import package.include.visual as visual                 #视觉相关（人脸识别）
import package.skills as skills                         #技能类（大脑）

#全局对象（主要是导入到插件相关进程中）
class public_obj(Base):

    def __init__(self):
        #当前用户ID,人脸识别内存变量
        self.uid =  mp.Value("h",0)
        #前后端通讯
        self.sw = mysocket.Mysocket()
        #定义插件间通讯的管道
        self.plugin_conn, self.master_conn = mp.Pipe(False)


'''初始化内部使用的对象（主要是导入到语音相关进程中）'''
class pyaudio_obj(Base):

    def __init__(self):
        self.yuyin_path = os.path.join(self.config['root_path'], 'data/yuyin')
        self.time,self.collections,self.sys,self.signal,self.wave,self.array,self.pack,self.so = time,collections,sys,signal,wave,array,pack,os

        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        CHUNK_DURATION_MS = 30                              # supports 10, 20 and 30 (ms)
        PADDING_DURATION_MS = 1500                          # 1 sec jugement

        self.RATE = 16000
        self.CHUNK_SIZE = int(self.RATE * CHUNK_DURATION_MS / 1000)   # chunk to read
        self.NUM_PADDING_CHUNKS = int(PADDING_DURATION_MS / CHUNK_DURATION_MS)
        self.NUM_WINDOW_CHUNKS = int(400 / CHUNK_DURATION_MS)    # 400 ms/ 30ms  ge
        self.NUM_WINDOW_CHUNKS_END = self.NUM_WINDOW_CHUNKS * 2

        pa = pyaudio.PyAudio()
        self.stream = pa.open(format= FORMAT,
                    channels = CHANNELS,
                    rate = self.RATE,
                    input = True,
                    start = False,
                    # input_device_index=2,
                    frames_per_buffer = self.CHUNK_SIZE)

        #0: Normal，1：low Bitrate， 2：Aggressive；3：Very Aggressive
        self.vad = webrtcvad.Vad(3)

'''主控制类'''

class Master(Base):

    def __init__(self):
        #设备检测
        self.check = check.Check()

        #初始化录音和识别
        self.Luyin_shibie =  yuyin.Luyin_shibie()

        self.mqtt = mymqtt.Mymqtt(self.config)

        #技能总控
        self.skills = skills.Skills()

        #全局对象类
        self.public_obj = public_obj()

    '''
    命令动作执行_成功回调
        reobj       --  成功返回 JSON 格式对象
        {
            'state': True',                     返回状态：True 成功 / False 失败
            'data': '想知道吗？你求我呀。',     返回提示语，会显示到前端
            'type': 'tuling',                   返回类型：tuling 机器人应答 / system 系统应答（包含插件）
            'msg': '图灵回复成功！'             返回类型中文提示语，仅供调试使用
        }
    '''
    def command_success(self, reobj = {} ):
        log.info("命令动作执行_成功", reobj )

        #发送到前面屏幕
        send_txt = {'obj':'mojing','msg': reobj['data']}
        self.public_obj.sw.send_info( send_txt )
        del send_txt

        #合成语音并播放
        yuyin.Hecheng_bofang(self.is_snowboy).main( reobj )



    '''命令动作执行
    参数:
        sbobj -- 语音识别成功返回的字典对象,格式体如下：
        {
            'state': True,                 -- 操作状态
            'enter': 'voice',               -- 入口（voice-语音、camera-摄像头、mqtt）
            'optype': 'action'              -- 操作类型（action动作 / snowboy唤醒）
            'type': 'system',               -- 控制类型（系统类型-合成语音会被缓存）
            'msg': '识别失败！',            -- 操作状态中文提示
            'data': '我没听清你说了啥',     -- 返回文本（屏幕提示）
        }
    '''
    def command_execution(self, sbobj ):
        log.info("进入主控", sbobj )

        #语音识别成功
        if sbobj["state"]:

            #发送到前面屏幕
            if sbobj['data']:

                if sbobj['enter'] =="mqtt":
                    send_txt = {'obj':'zhuren','msg': "微信小程序控制" }
                else:
                    send_txt = {'obj':'zhuren','msg': sbobj['data'] }

                self.public_obj.sw.send_info( send_txt )

            #=========================================================================
            #发送通知给技能
            sbobj['optype'] = 'action'
            self.public_obj.master_conn.send(sbobj)

        else:
            self.is_snowboy.value = 0

        if sbobj['enter'] != 'voice':
            self.is_snowboy.value = 0


    #开始启动大脑（技能）模块
    def start_skills(self):
        self.p5 = mp.Process(
            target = self.skills.main,
            args = (self.command_success, self.public_obj)
        )
        self.p5.start()


    ''''
    进入语音进程
    参数：
        is_one - 是否为首次唤醒 1- 首次 / 2 - 第二次（不在播放唤醒应答声）
    '''
    def start_yuyin(self, is_one = 0):
        if is_one == 2:
            self.public_obj.master_conn.send({"optype":"snowboy"})

        log.info("开始进入语音进程")
        if self.hx_yuyinpid.value > 0:
            os.system("sudo kill -9 {}".format(self.hx_yuyinpid.value))

        self.hx_yuyinpid.value = 0

        #启动新进程开始录音+识别
        self.p2 = mp.Process(
            target = self.Luyin_shibie.main,
            args = (self.hx_yuyinpid, is_one, self.command_execution, pyaudio_obj(), self.public_obj )
        )
        self.p2.start()


    #语音唤醒成功
    def snowboy_success(self):
        self.is_snowboy.value = 1
        self.public_obj.master_conn.send({"optype":"snowboy"})


    #开始启动唤醒
    def start_snowboy(self):

        model  = os.path.join(self.config['root_path'],self.config['WAKEUP']['model'])      #语音唤醒模型
        sensit = self.config['WAKEUP']['sensit']

        resource = os.path.join(self.config['root_path'],'data/snowboy/common.res')

        #用新进程启动唤醒
        self.p1 = mp.Process(
            target = snowboy.Snowboy().main,
            args = (self.snowboy_success, model, sensit, resource )
        )
        self.p1.start()
        del model,sensit,resource


    #人脸识别
    def start_face(self):
        self.p3 = mp.Process(
            target = visual.Visual().main,
            args = (self.command_execution, )
        )
        self.p3.start()


    #启动MQTT通信服务
    def start_mqtt(self):
        self.p4 = mp.Process(
            target = self.mqtt.main,
            args = (self.command_execution, self.public_obj )
        )
        self.p4.start()

    def main(self):
        #定义唤醒成功内存变量：记录语音进程ID
        self.hx_yuyinpid = mp.Value("h",0)
        #定义唤醒成功内存变量：是否唤醒成功
        self.is_snowboy  = mp.Value("h",0)

        #启动MQTT服务
        self.start_mqtt()

        #启动设备检测
        self.check.main(self.public_obj)

        #启动唤醒
        self.start_snowboy()

        #启动技能
        self.start_skills()

        #是否启动人脸识别：文件不存在则启动人脸识别
        is_face = os.path.join(self.config['root_path'],'data/is_face')

        #计时变量
        timeing = 0

        while True:

            #监听唤醒进程：是否正常
            if self.p1.is_alive()==False:
                self.start_snowboy()
                time.sleep(3)

            #监听语音唤醒：是否唤醒
            if self.is_snowboy.value > 0:
                self.start_yuyin( self.is_snowboy.value )
                self.is_snowboy.value = 0

            #开始人脸识别
            if os.path.isfile(is_face) is False:
                self.start_face()
                os.mknod(is_face)       #创建空文件

            timeing += 1
            if timeing >= 4:
                timeing = 0
                gc.collect()        #回收内存

            time.sleep(0.5)