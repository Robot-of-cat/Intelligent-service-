# -*- coding: utf-8 -*-
import requests,re
from package.base import Base,log

#切记不要点开密钥，不然会有意想不到的情况
class Tuling(Base):

    def __init__(self):
        self.KEY     = self.config['TULING']['key']        #图灵KEY
        self.apiUrl  = self.config['TULING']['url']

    '''zhixing# 对外调用接口
    参数：
        name:需要输入图灵交流的文字。字符串类型'
    返回：
        正常:返回图灵的对话  类型：字符串
        网络异常:返回No_network#没有网络   类型：字符串
        异常：返回你传入的参数类型错误  类型：字符串
    '''
    def main(self,name):
        try:
            if self.mylib.typeof(name) != 'str':
                return {'state':False,'data': '我不知道你说了啥','type':'system', 'msg':'参数1，需要输入图灵交流的文字。字符串类型！'}

            data = {'key': self.KEY,'info': name,'userid': '111111'}

            biangliang = requests.post(self.apiUrl,data=data,verify=True,timeout=2).json()['results'][0]['values']['text']
            biangliang = re.sub( r"http[s]?\/\/.+","", biangliang, re.M|re.I)
            del data
            return {'state':True,'data': biangliang,'type':'tuling','msg':'图灵回复成功！'}

        except Exception as bug:
            log.warning('超时s',bug)
            return {'state':False,'data':'网络可能有点问题，请检查一下网络。','type':'system','msg':'连接图灵服务器超时！'}

if __name__ == '__main__':


    print( Tuling().main('1314'))