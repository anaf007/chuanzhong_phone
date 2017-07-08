#coding=utf-8
import re,urllib2,wx,threading,lxml
from lxml import etree
import os,time,commands,subprocess
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from bs4 import BeautifulSoup
import datetime

#sqlalchemy
from sqlalchemy import Column, String, create_engine,Integer,Sequence,DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
# engine = create_engine('mysql://root:@localhost:3306/chuanzong?charset=utf8', echo=True)
engine = create_engine('mysql://root:@localhost:3306/chuanzong?charset=utf8')
Base = declarative_base()
Session = sessionmaker(bind=engine)
Session.configure(bind=engine)
session = Session()


"""
author:anaf
time:2017-06-29
note:使用wxpython做gui界面，
使用threading防止界面假死
使用urllib2爬取页面等 
使用BeautifulSoup
使用了url：http://www.oschina.net/code/snippet_736230_26816
来获取前一天一周一个月
"""


class Info(Base):
    __tablename__ = 'infos'
    id = Column(Integer, Sequence('info_id_seq'), primary_key=True)
    #公司名称
    title = Column(String(100))
    #联系人
    name = Column(String(10))
    #手机
    phone = Column(String(11))
    #邮箱
    email = Column(String(100))
    #路径
    url = Column(String(100))

    def __repr__(self):
        return "info:%s,%s"%(self.name,self.phone)

class send(Base):
    __tablename__ = 'sends'
    id = Column(Integer, Sequence('send_id_seq'), primary_key=True)
    phone = Column(String(11))
    email = Column(String(32))
    send_time = Column(DateTime, nullable=False)
    def __repr__(self):
        return "send:%s,%s"%(self.phone,self.send_time)

class Main(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None,-1,u'号码读取器',size=(500,500))
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.panel = wx.Panel(self, wx.ID_ANY)
        self.info = []
        #活动标志，防止线程数添加重复位于setStartSms函数使用
        self.active = 0

        
        wx.StaticText(self.panel, -1, u"地址",pos=(20,20)).SetFont(font=wx.Font(16, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.url = wx.TextCtrl(self.panel,-1,u'',pos=(100,20),size=(350,30))
        
        wx.StaticText(self.panel, -1, u"手机号",pos=(20,70)).SetFont(font=wx.Font(16, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.phone = wx.TextCtrl(self.panel,-1,u'',pos=(100,70),size=(350,30))
        
        # wx.StaticText(self.panel, -1, u"XPATH",pos=(20,120)).SetFont(font=wx.Font(16, wx.SWISS, wx.NORMAL, wx.BOLD))
        # self.xpath = wx.TextCtrl(self.panel,-1,u"/descendant::div[@id='pagebox']/a/@href",pos=(100,120),size=(350,30))
        
        self.startChuanzongBtn = wx.Button(self.panel,-1,u'读取传众',pos=(25,100),size=(200,30))
        self.searchHuangye88Btn = wx.Button(self.panel,-1,u'读取黄页88',pos=(250,100),size=(200,30))
        self.startChuanzongBtn.Bind(wx.EVT_BUTTON,self.OnStartBtn)
        self.searchHuangye88Btn.Bind(wx.EVT_BUTTON,self.gethuangye88all_a)

        self.messageText = wx.TextCtrl(self.panel,-1,pos=(20,150),size=(460,250),style=wx.TE_MULTILINE|wx.TE_RICH2| wx.TE_READONLY | wx.TE_MULTILINE | wx.BORDER_NONE)
        os.system('adb server')
        
        
        self.messageText.AppendText(u'初始化手机')

        
    def OnCloseWindow(self, event):
        self.Destroy()

    def OnStartBtn(self,event):
        url = self.url.GetValue().strip()
        headers = {'User-Agent' : 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.96 Mobile Safari/537.36'}
        if url =='':
            return
        self.messageText.AppendText(u'\n'+u'开始读取网页信息...')
        self.messageText.AppendText(u'\n'+url)

        response = urllib2.Request(url = url,headers = headers)
        ReadHtml(self,url,response,headers).start()

    def gethuangye88all_a(self,event):
        url = self.url.GetValue().strip()
        headers = {'User-Agent' : 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.96 Mobile Safari/537.36'}
        if url =='':
            return
        self.messageText.AppendText(u'\n'+u'开始读取网页信息...')
        self.messageText.AppendText(u'\n'+url)

        
        for i in range(1,60):
            if i == 1:
                ReadHuangye88Html(self,url+"?from=m",i).start()
            else:
                ReadHuangye88Html(self,url+"pn%d/?from=m"%i,i).start()

        #检查线程数量
        eqThread0(self).start()
        


    def setMessageText(self,text):
        self.messageText.AppendText(text)

    def setValueText(self,infolist):
        self.info.append(infolist)
        self.messageText.AppendText(u"\n索引：%s，号码：%s,姓名：%s,共%s个"%(infolist[4],infolist[1],infolist[0],str(len(self.info))))
        # self.messageText.AppendText('\n目前添加'+str(len(self.info))+u'个电话')


    def day_month_bet(self,d):
        oneday = datetime.timedelta(days=30)
        day = d - oneday
        date_from = datetime.datetime(day.year, day.month, day.day, 0, 0, 0)
        date_to = datetime.datetime(d.year, d.month, d.day, 23, 59, 59)
        return (str(date_from), str(date_to))


    def setStartSms(self):
        if threading.activeCount()==1:
            #防止重复
            if self.active == 1:
                return 
            self.active = 1
            datalist = []
            datalistsend = [] 
            d = datetime.datetime.now()
            month = self.day_month_bet(d)
            phonelist = []

            #获取所有手机号码
            for i in session.query(Info.phone).all():
                datalist.append(i[0])
            #近一个月已发送的的手机号
            for i in session.query(send).filter(send.send_time>month[0],send.send_time<month[1]).group_by(send.phone).all():
                datalistsend.append(i.phone)

            for i in self.info:
                #如果最近一个月已经发送过的话
                if i[1] in datalistsend:
                    self.setMessageText(u'\n手机号码：%s最近一个月已经发送过短信了'%i[1])
                    continue

                #排除重复的号码
                if i[1] not in phonelist:
                    phonelist.append(i[1])
                    self.setMessageText(u'\n时间：'+time.strftime('%Y-%m-%d %H:%M:%S')+u'，手机号：'+str(i[1]))
                    # self.send_sms(i[1])
                    self.setMessageText(u'...短信已发送')
                    session.add(send(phone=i[1][0:11],send_time=time.strftime('%Y-%m-%d %H:%M:%S')))
                    if i[1] not in datalist:
                        session.add(Info(title=i[2][0:100],name=i[0][0:4],phone=i[1][0:11],email='',url=i[3][0:100]))

            try:
                session.commit()
            except Exception, e:
                session.rollback()
                print u'错误: %s'%str(e)
            self.setMessageText(u'\n'+u'读取结束...')


    #发送短信
    def send_sms(self,phone):
        body = "南宁200元网站建设，软件设计定制开发等软件服务，可托管或交付代码。详情访问网站h.anaf.cn，个人接单，如您刚好有软件需求请回电详询"
        subprocess.call(["adb", "shell", "am", "start",
                "-a", "android.intent.action.SENDTO",
                "-d", "sms:%s" % phone,
                "--es", "sms_body", '"%s"' % body])
        subprocess.call(["adb", "shell", "sleep", "1"])
        for i in range(8):
            subprocess.call(["adb", "shell", "input", "keyevent", "20"])
        for i in range(10):
            subprocess.call(["adb", "shell", "input", "keyevent", "22"])
        subprocess.call(["adb", "shell", "sleep", "1"])
        subprocess.call(["adb", "shell", "input", "keyevent", "66"])
        subprocess.call(["adb", "shell", "sleep", "2"])
        subprocess.call(["adb", "shell", "input", "keyevent", "66"])
        subprocess.call(["adb", "shell", "sleep", "1"])
        os.system('adb shell input keyevent 4')
        subprocess.call(["adb", "shell", "sleep", "1"])
        os.system('adb shell input keyevent 3')
        subprocess.call(["adb", "shell", "sleep", "1"])


class eqThread0(threading.Thread):
    def __init__(self,windows):
        threading.Thread.__init__(self)
        threading.Event().clear()
        self.window = windows
    def run(self):
        while(True):
            time.sleep(5)
            if  threading.activeCount()==2:
                wx.CallAfter(self.window.setStartSms)
                break 




#黄页88
class ReadHuangye88Html(threading.Thread):
    def __init__(self,windows,url,x):
        threading.Thread.__init__(self)
        threading.Event().clear()
        self.window = windows
        self.url = url
        self.x = x

    #发送短信
    def send_sms(self,phone):
        body = "南宁200元网站建设，软件设计定制开发等软件服务，可托管或交付代码。详情访问网站h.anaf.cn，个人接单，如您刚好有软件需求请回电详询"
        subprocess.call(["adb", "shell", "am", "start",
                "-a", "android.intent.action.SENDTO",
                "-d", "sms:%s" % phone,
                "--es", "sms_body", '"%s"' % body])
        subprocess.call(["adb", "shell", "sleep", "1"])
        for i in range(8):
            subprocess.call(["adb", "shell", "input", "keyevent", "20"])
        for i in range(10):
            subprocess.call(["adb", "shell", "input", "keyevent", "22"])
        subprocess.call(["adb", "shell", "sleep", "1"])
        subprocess.call(["adb", "shell", "input", "keyevent", "66"])
        subprocess.call(["adb", "shell", "sleep", "2"])
        subprocess.call(["adb", "shell", "input", "keyevent", "66"])
        subprocess.call(["adb", "shell", "sleep", "1"])
        os.system('adb shell input keyevent 4')
        subprocess.call(["adb", "shell", "sleep", "1"])
        os.system('adb shell input keyevent 3')
        subprocess.call(["adb", "shell", "sleep", "1"])

    def day_month_bet(self,d):
        oneday = datetime.timedelta(days=30)
        day = d - oneday
        date_from = datetime.datetime(day.year, day.month, day.day, 0, 0, 0)
        date_to = datetime.datetime(d.year, d.month, d.day, 23, 59, 59)
        return (str(date_from), str(date_to))


    def run(self):
        
        headers = {'User-Agent' : 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.96 Mobile Safari/537.36'}
        x = 1
        infolist = []
        response = urllib2.Request(url = self.url,headers = headers)
        try:
            if self.x>=5 and self.x<10:
                time.sleep(3)
            if self.x>=10 and self.x<20:
                time.sleep(10)
            if self.x>=20 and self.x<30:
                time.sleep(15)
            if self.x>=30 and self.x<40:
                time.sleep(20)
            if self.x>=40:
                time.sleep(25)
            content = urllib2.urlopen(response).read()
            
        except Exception, e:
            # wx.CallAfter(self.window.setStartSms)
            return
        bsObj = BeautifulSoup(content)
        jubao = bsObj.find(id='jubao')

        if not jubao:
            wx.CallAfter(self.window.setMessageText,u'\n索引：%s没有内容,剩余线程数%s'%(str(self.x),threading.activeCount()-2))
            # wx.CallAfter(self.window.setStartSms)
            return 
        for i in jubao.find_all('dl'):
            try:
                title = i.dt.h4.a.get_text()
                if not i.dt.span.a.get_text():
                    continue
                phone = re.findall('1[3|4|5|7|8]\d{9}',i.dt.span.a.get_text())[0]
                qiyeurl = i.dt.span.a.get('href')
                if not phone:
                    continue
                response = urllib2.Request(url = qiyeurl+'?from=m',headers = headers)
                try:
                    content = urllib2.urlopen(response).read()
                except Exception, e:
                    lianxiren =  u'504无法获取姓名'%str(phone)
                    continue
                bsObjx = BeautifulSoup(content)

                lianxiren = bsObjx.find_all(class_='l-txt none')[1].li.a.get_text()
                
                wx.CallAfter(self.window.setValueText,[lianxiren,phone,title,qiyeurl,self.x])
            except Exception, e:
                continue

        wx.CallAfter(self.window.setMessageText,u'\n索引：%s内容摘取完成,剩余线程数%s'%(str(self.x),threading.activeCount()-2))
        





#传众的手机号码
class ReadHtml(threading.Thread):
    def __init__(self,windows,url,response,headers):
        threading.Thread.__init__(self)
        threading.Event().clear()
        self.window = windows
        self.url = url
        self.response = response
        self.headers = headers
    #发送短信
    def send_sms(self,phone):
        body = "南宁200元网站建设，软件设计定制开发等软件服务，可托管或交付代码。详情访问网站h.anaf.cn，个人接单，如您刚好有软件需求请回电详询"
        subprocess.call(["adb", "shell", "am", "start",
                "-a", "android.intent.action.SENDTO",
                "-d", "sms:%s" % phone,
                "--es", "sms_body", '"%s"' % body])
        subprocess.call(["adb", "shell", "sleep", "1"])
        for i in range(8):
            subprocess.call(["adb", "shell", "input", "keyevent", "20"])
        for i in range(10):
            subprocess.call(["adb", "shell", "input", "keyevent", "22"])
        subprocess.call(["adb", "shell", "sleep", "1"])
        subprocess.call(["adb", "shell", "input", "keyevent", "66"])
        subprocess.call(["adb", "shell", "sleep", "2"])
        subprocess.call(["adb", "shell", "input", "keyevent", "66"])
        subprocess.call(["adb", "shell", "sleep", "1"])
        os.system('adb shell input keyevent 4')
        subprocess.call(["adb", "shell", "sleep", "1"])
        os.system('adb shell input keyevent 3')
        subprocess.call(["adb", "shell", "sleep", "1"])

    def run(self):
        d = datetime.datetime.now()
        month = self.day_month_bet(d)

        phonelist = []
        wx.CallAfter(self.window.setMessageText,u'\n'+u'循环读取网页信息...')
        headers = {'User-Agent' : 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.96 Mobile Safari/537.36'}
        content = urllib2.urlopen(self.response).read()
        bsObj = BeautifulSoup(content)
        forbs = bsObj.find(id='pagebox')
        datalist = []
        datalistsend = [] 

        #获取所有手机号码
        for i in session.query(Info.phone).all():
            datalist.append(i[0])
        #近一个月已发送的的手机号
        for i in session.query(send).filter(send.send_time>month[0],send.send_time<month[1]).group_by(send.phone).all():
            datalistsend.append(i.phone)


        for i in forbs.find_all('a')[0:-1]:
            response = urllib2.Request(url =i.get('href'),headers = headers)
            content = urllib2.urlopen(response).read()
            bsObj = BeautifulSoup(content)
            for i in  bsObj.find_all(class_='company-mesage'): 
                #获取公司名称
                title = i.find(class_='row right').a.get_text()
                url = i.find(class_='row right').a.get('href')
                j = i.find(class_='row word')
                fx = j.find_all(class_='col-sm-6')
                #名称
                name = fx[0].get_text().strip().replace(' ','').replace('\n','').replace(u'联系人：','')  
                #电话
                phone = fx[2].get_text().strip().replace(' ','').replace('\n','').replace(u'手机：','')    
                #邮箱
                email = fx[3].get_text().strip().replace(' ','').replace('\n','').replace(u'邮箱：','')    
                if phone is None or phone =='':
                    continue

                #如果最近一个月已经发送过的话
                if phone in datalistsend:
                    wx.CallAfter(self.window.setMessageText,u'\n手机号码：%s最近一个月已经发送过短信了'%phone)
                    continue

                #排除重复的号码
                if phone not in phonelist:
                    phonelist.append(phone)
                    wx.CallAfter(self.window.setMessageText,u'\n时间：'+time.strftime('%Y-%m-%d %H:%M:%S')+u'，手机号：'+phone)
                    #发送手机短信
                    self.send_sms(phone)
                    #添加发送手机号码
                    session.add(send(phone=phone,send_time=time.strftime('%Y-%m-%d')))
                    
                    wx.CallAfter(self.window.setMessageText,u'...短信已发送')

                #如果没有添加到数据库：
                if phone not in datalist:
                    session.add(Info(title=title,name=name,phone=phone,email=email,url=url))
            
                
        try:
            session.commit()
        except Exception, e:
            session.rollback()
            print 'cuowu %s'%str(e)
        wx.CallAfter(self.window.setMessageText,u'\n'+u'读取结束...')

    
    #获取30天内

    def day_month_bet(self,d):
        oneday = datetime.timedelta(days=30)
        day = d - oneday
        date_from = datetime.datetime(day.year, day.month, day.day, 0, 0, 0)
        date_to = datetime.datetime(d.year, d.month, d.day, 23, 59, 59)
        return (str(date_from), str(date_to))

    #获取上周
    def week_get(self,d):
        dayscount = datetime.timedelta(days=d.isoweekday())
        dayto = d - dayscount
        sixdays = datetime.timedelta(days=6)
        dayfrom = dayto - sixdays
        date_from = datetime.datetime(dayfrom.year, dayfrom.month, dayfrom.day, 0, 0, 0)
        date_to = datetime.datetime(dayto.year, dayto.month, dayto.day, 23, 59, 59)
        print '---'.join([str(date_from), str(date_to)])

    #获取上个月
    def month_get(self,d):
        dayscount = datetime.timedelta(days=d.day)
        dayto = d - dayscount
        date_from = datetime.datetime(dayto.year, dayto.month, 1, 0, 0, 0)
        date_to = datetime.datetime(dayto.year, dayto.month, dayto.day, 23, 59, 59)
        return (str(date_from), str(date_to))


if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = Main()
    frame.Show()
    app.MainLoop()




