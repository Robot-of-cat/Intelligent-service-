#!/usr/bin/python3
# -*- coding: UTF-8 -*-
import os,sys,re,time
import multiprocessing as mp        #多进程

this_path = os.path.dirname(os.path.dirname(__file__))
task_main       = 'main.py'                         #后端任务
task_main_cmd   = os.path.join(this_path,'python/'+task_main)

task_mojing     = 'moJing'                          #前端任务
task_mojing_cmd = os.path.join(this_path,'app/'+task_mojing)   #前端任务
task_run        = os.path.basename(__file__)        #监控任务

logfile = os.path.join(this_path,'python/runtime/log/tasks.log')	# 日志文件

#停止任务
def stop( task_name ):
    taskcmd = 'ps ax | grep ' + task_name
    out = os.popen(taskcmd).read();               # 检测是否已经运行
    pat = re.compile(r'(\d+).+('+task_name+')')
    res = pat.findall(out)
    for x in res:
        pid = x[0]
        cmd = 'sudo kill -9 '+ pid
        out = os.popen(cmd).read()
    print('[\033[31m停止\033[0m] 任务成功！')

#查询任务
def ps_ax( task_name ):
    taskcmd = 'ps ax | grep ' + task_name
    out = os.popen(taskcmd).read();               # 检测是否已经运行
    pat = re.compile(r'(\d+).+('+task_name+')')
    res = pat.findall(out)
    if len(res)>2:
        return True
    else:
        return False

# 开始启动
def start(run_file, cmdtype ='system'):

    #启动函数
    def run_fund(run_file, cmdtype ='system'):
        cmd = 'export DISPLAY=:0 && '+ run_file
        if cmdtype == 'system':
            os.system(cmd)
        else:
            os.popen(cmd)

    mp.Process(
        target = run_fund,
        args = (run_file,cmdtype)
    ).start()

#3秒后关闭等待动画,等待3秒是确保动画已经自启后我们在关闭
def animation():
    time.sleep(3)
    os.system("sudo pkill -TERM bannerd")
    time.sleep(5)
    os.system("sudo pkill -TERM bannerd")
    time.sleep(5)
    os.system("sudo pkill -TERM bannerd")
    time.sleep(20)
    os.system("sudo pkill -TERM bannerd")

#启动Mojing前端
def start_mojing_app():
    #关闭等待动画
    main_animation= mp.Process(target = animation)
    main_animation.start()

    #麦克风利用率100%
    os.system("sudo amixer set Capture 90%")
    os.system("sudo ntpdate ntp.sjtu.edu.cn")

    while True:
        is_task_mojing = ps_ax(task_mojing)
        if is_task_mojing == False:
            #start(task_mojing_cmd, 'system')
            start(task_mojing_cmd + ' Debug', 'system')     #启动前端

            stop(task_main)
            time.sleep(3)

            start('sudo '+task_main_cmd, 'system')          #启动后端

        time.sleep(3)

if __name__ == '__main__':
    if len(sys.argv)>1:
        argv = sys.argv[1]
    else:
        argv = ""

    if argv == 'stop':
        stop(task_main)
        stop(task_mojing)
        stop(task_run)
    elif argv == 'restart':
        stop(task_main)
        stop(task_mojing)

    #检测自己有没有运行
    runcmd = 'ps ax | grep ' + task_run
    out = os.popen(runcmd).read();               # 检测是否已经运行
    pat = re.compile(r'(\d+).+(\/python\d?\s+\S+'+task_run+')')
    runres = pat.findall(out)
    if len(runres) > 1:
        exit()

    start_mojing_app()
