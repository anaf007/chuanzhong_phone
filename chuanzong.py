#coding=utf-8
import re,urllib2,wx,threading
from lxml import etree
"""
author:anaf
time:2017-06-29
note:使用wxpython做gui界面，
使用threading防止界面假死
使用urllib2爬取页面等 
re正则匹配手机号码
lxml获取页数
"""

class Main(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self,None,-1,u'号码读取器',size=(500,500))
		self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
		self.panel = wx.Panel(self, wx.ID_ANY)
		
		wx.StaticText(self.panel, -1, u"URL",pos=(20,20)).SetFont(font=wx.Font(16, wx.SWISS, wx.NORMAL, wx.BOLD))
		self.url = wx.TextCtrl(self.panel,-1,u'http://www.czvv.com/450000/jichuang/',pos=(100,20),size=(350,30))
		
		wx.StaticText(self.panel, -1, u"REGEX",pos=(20,70)).SetFont(font=wx.Font(16, wx.SWISS, wx.NORMAL, wx.BOLD))
		self.regex = wx.TextCtrl(self.panel,-1,u'1[3|4|5|7|8]\d{9}',pos=(100,70),size=(350,30))
		
		wx.StaticText(self.panel, -1, u"XPATH",pos=(20,120)).SetFont(font=wx.Font(16, wx.SWISS, wx.NORMAL, wx.BOLD))
		self.xpath = wx.TextCtrl(self.panel,-1,u"/descendant::div[@id='pagebox']/a/@href",pos=(100,120),size=(350,30))
		
		self.startBtn = wx.Button(self.panel,-1,u'读取',pos=(25,150),size=(450,30))
		self.startBtn.Bind(wx.EVT_BUTTON,self.OnStartBtn)

		self.messageText = wx.TextCtrl(self.panel,-1,pos=(20,190),size=(460,280),style=wx.TE_MULTILINE|wx.TE_RICH2| wx.TE_READONLY | wx.TE_MULTILINE | wx.BORDER_NONE)

		

	def OnCloseWindow(self, event):
		self.Destroy()

	def OnStartBtn(self,event):
		url = self.url.GetValue().strip()
		regex = self.regex.GetValue().strip()
		xpath = self.xpath.GetValue().strip()

		headers = {'User-Agent' : 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.96 Mobile Safari/537.36'}
		response = urllib2.Request(url = url,headers = headers)
		self.messageText.AppendText(u'\n'+u'开始读取网页信息...')
		ReadHtml(self,url,regex,xpath,response,headers).start()

	def setMessageText(self,text):
		self.messageText.AppendText(text)

			

class ReadHtml(threading.Thread):
    def __init__(self,windows,url,regex,xpath,response,headers):
        threading.Thread.__init__(self)
        threading.Event().clear()
        self.window = windows
        self.url = url
        self.regex = regex
        self.xpath = xpath
        self.response = response
        self.headers = headers
    def run(self):
    	content = urllib2.urlopen(self.response).read()
    	tree1 = etree.HTML(content)
    	nodes1 = tree1.xpath(self.xpath)
    	phonelist = []
    	nodes1 =  nodes1[0:-1]
    	wx.CallAfter(self.window.setMessageText,u'\n'+u'循环读取网页信息...')
    	for i in nodes1:
    		response = urllib2.Request(url = i,headers = self.headers)
    		content = urllib2.urlopen(response).read()
    		for j in re.findall(self.regex,content):
    			if j not in phonelist:
    				phonelist.append(j)
    				wx.CallAfter(self.window.setMessageText,u'\n'+j)
    	wx.CallAfter(self.window.setMessageText,u'\n'+u'读取结束...')
    	
    	

if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = Main()
    frame.Show()
    app.MainLoop()

