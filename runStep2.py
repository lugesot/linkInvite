import time
import os.path
import urllib
import logging,os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
import redis

#搜索用户的账号
def main():

    accounts = []
    accountFile = "accounts.txt"
    

    si = SendInvitation(accounts)
    if si.testRedis() == True:
        si.readAccount(accountFile)
        si.swichNextUser()
        si.iterateTarget()
        si.close()

#element.close()
class SendInvitation(object):
    def __init__(self,accounts):
        self.accountIndex = -1
        self.connectUserLimit = 200   #每个账户一天最多添加的用户数
        self.reidsClient = redis.Redis(host='127.0.0.1', port=6379)
        self.sharedConnectionsKey = "sharedConnections"
        self.logger = self.get_logger()
    
    #format username password\n
    def readAccount(self, fileName):
        self.accounts = []
        d = os.getcwd()
        fileName=d +'/'+fileName 
        try:
            with open(fileName, 'r', encoding="utf-8") as file:
                while True:
                    line = file.readline()
                    if not line:
                        break 
                    words = line.strip().split()
                    if len(words)==2:
                        self.accounts.append([words[0],words[1]])
            if len(self.accounts)==0:
                raise Exception("账户信息为空，请检查格式，每行: 用户名 空格 密码")
        except FileNotFoundError as fnf:
            self.logger.debug("linkin账号文件 {0} 不存在".format(fileName))
            raise
        #print(self.accounts)

    # def readMessage(self, fileName):
    #     d = os.getcwd()
    #     fileName=d +'/'+fileName 
    #     self.message = ""
    #     with open(fileName, 'r', encoding="utf-8") as file:
    #         self.message = file.read()
    #     print("邀请样式:" + self.message)
    def readMessage(self,path,fileName):
        fileName = path +'/'+fileName 
        self.message = ""
        with open(fileName, 'r', encoding="utf-8") as file:
            self.message = file.read()
        self.logger.debug("邀请样式:" + self.message)

    #领英限制：每个账户一天只能邀请100人
    def swichNextUser(self):
        self.accountIndex = self.accountIndex +1
        if self.accountIndex>=len(self.accounts):
            raise Exception("无account可用了，名额都已用尽")
        self.accountName = self.accounts[self.accountIndex][0]
        self.logger.debug("已切换到用户：" + self.accountName)

        while self.checkLimitByRedis() == False:
            self.accountIndex = self.accountIndex +1
            if self.accountIndex>=len(self.accounts):
                raise Exception("无account可用了，名额都已用尽")
            self.accountName = self.accounts[self.accountIndex][0]

        self.accountName = self.accounts[self.accountIndex][0]
        self.accountPassword = self.accounts[self.accountIndex][1]
        options = webdriver.ChromeOptions()
        options.add_argument("--incognito") #隐身模式
        #driver_path = "C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe"  # chromedriver.exe 的路径
        #driver = webdriver.Chrome(executable_path=driver_path, options=options)
        self.driver = webdriver.Chrome(options=options)
        time.sleep(0.5)
        self.driver.get("https://www.linkedin.com")
        self.driver.implicitly_wait(5)
        element = self.driver.find_element_by_name("session_key")
        element.send_keys(self.accountName)
        element = self.driver.find_element_by_name("session_password")
        element.send_keys(self.accountPassword)
        element.send_keys(Keys.RETURN)

    def mainPage(self, pageLink):
        myHomePage = self.driver.window_handles[0]
        self.driver.switch_to.window(myHomePage)
        self.driver.implicitly_wait(1)
        newWindow = "window.open('"+pageLink+"');"
        self.driver.execute_script(newWindow)
        toHandle = self.driver.window_handles[1]
        self.driver.switch_to.window(toHandle)
        self.driver.implicitly_wait(5)

        connectBtnXpath = '//main//section//button[contains(@class,"pv-s-profile-actions--connect")]'
        try:
            locator = (By.XPATH, connectBtnXpath)
            WebDriverWait(self.driver, 8, 0.5).until(EC.element_to_be_clickable(locator))
        except TimeoutException as te:
            self.logger.debug("检查是否 是否通过more按钮 connect")
            moreBtnXpath = '//main//section//span[@class="artdeco-button__text" and contains(text(),"More…") ]'
            moreBtns = self.driver.find_elements_by_xpath('//span[@class="artdeco-button__text"]')
            moreBtn = None
            for btn in moreBtns:
                if btn.text == "More…":
                        moreBtn = btn
                        break
            if (moreBtn == None):
                raise Exception("More button没找到: " + pageLink)
            #moreBtn = moreBtn.parent
            moreBtn.click()
            time.sleep(0.5)
            try:
                connPath = '//main//section//artdeco-dropdown-item[contains(@class,"pv-s-profile-actions--connect")]'
                locator = (By.XPATH, connPath)
                WebDriverWait(self.driver, 2, 0.5).until(EC.element_to_be_clickable(locator))
            except TimeoutException as te3:
                self.logger.debug("已经是好友: " + pageLink)
            else:
                self.clickConnectBtn(connPath, pageLink)

        except Exception as e:
            self.logger.debug("异常发生："+e)
            self.logger.debug("页面地址："+pageLink)
        else:
            self.clickConnectBtn(connectBtnXpath, pageLink)
        finally:
            self.driver.close()
        pass
    
    def clickConnectBtn(self, btnXPah, pageLink):
        #self.logger.debug("connect btn found")
        connectBtn = self.driver.find_element_by_xpath(btnXPah)
        connectBtn.click()
        time.sleep(2)
        addNoteBtn = self.driver.find_element_by_xpath("//button[@aria-label='Add a note']")
        addNoteBtn.click()
        time.sleep(0.5)
        note = self.driver.find_element_by_xpath("//textarea[@id='custom-message']")
        note.clear()
        note.send_keys(self.message)
        time.sleep(1)
        sendInvitaionBtn = self.driver.find_element_by_xpath("//button[@aria-label='Send invitation']")
        # 发出邀请
        sendInvitaionBtn.click()
        time.sleep(0.5)
        # 判断是否添加联系用户受限制
        try:
            limitBtn = self.driver.find_element_by_xpath("//button[@data-control-name='fuse_limit_got_it']")
        except NoSuchElementException:
            # 成功发出邀请
            self.recordResult(self.accountName, pageLink)
            pass
        else :
            self.logger.debug("!!!使用账号" + self.accountName + "添加受限，用户：" + pageLink)
            # 如何limitBtn存在，则抛异常
            raise InvitationLimitError(self.accountName, pageLink)
    
    def checkLimitByRedis(self):
        today = time.strftime("%Y%m%d", time.localtime())
        keyName = self.accountName + today
        if self.reidsClient.exists(keyName):
            if int(self.reidsClient.get(keyName))<=self.connectUserLimit:
                return True
            else:
                return False
        else:
            self.reidsClient.set(keyName, 0)

        return True
        pass

    def recordResult(self, userName, pageLink):
        memberPublicId = self.getPublicIdFromLink(pageLink)
        self.reidsClient.sadd(self.sharedConnectionsKey, memberPublicId)
        self.logger.debug("发送邀请给用户:" + memberPublicId + " ~ " + pageLink)

        today = time.strftime("%Y%m%d", time.localtime())
        keyName = self.accountName + today
        if self.reidsClient.exists(keyName):
            count = int(self.reidsClient.incr(keyName))
            if count > self.connectUserLimit:
                raise InvitationLimitError(userName, pageLink)
        else:
            self.reidsClient.set(keyName, 1)
        pass
    
    def iterateTarget(self):
        d = os.getcwd()
        items = os.listdir(d)
        for item in items:
            path = os.path.join(d, item)
            if os.path.isdir(path):
                if item.startswith('target') == True:
                    self.handleFolder(path)
        pass

    def handleFolder(self, path):
        self.logger.debug("正在处理文件夹：" + path)
        self.readMessage(path, "message.txt")
        items = os.listdir(path)
        for item in items:
            fullPath = os.path.join(path, item)
            if os.path.isdir(fullPath) == False:
                if item.startswith('message') == False:
                    self.inviteUserList(fullPath)
        pass

    def inviteUserList(self, fileName):
        try:
            with open(fileName, 'r', encoding="utf-8") as file:
                self.logger.debug("正在处理文件：" + fileName)
                while True:
                    userMainPageLink = file.readline()
                    if not userMainPageLink: 
                        break
                    userMainPageLink = userMainPageLink.strip()
                    if self.isSharedMember(userMainPageLink) == True:
                        continue

                    while True:
                        try:
                            self.mainPage(userMainPageLink)
                            break  #处理完该用户后，读下一行用户
                        except InvitationLimitError as e:   
                            self.swichNextUser()
                            continue
                        except Exception as e:
                            break
        except FileNotFoundError as fnf:
            self.logger.debug("{0}文件不存在".format(fileName))
            raise 
        pass

    def isSharedMember(self, userMainPageLink):
        memberPublicId = self.getPublicIdFromLink(userMainPageLink)
        isMember = self.reidsClient.sismember(self.sharedConnectionsKey, memberPublicId)
        if isMember == True:
            self.logger.debug("this is a shared member:" + memberPublicId)
        return isMember
    
    def getPublicIdFromLink(self, userMainPageLink):
        if userMainPageLink[-1] == '/':
            userMainPageLink = userMainPageLink[0:-1]
        arr = userMainPageLink.split("/")
        memberPublicId = urllib.parse.unquote(arr[len(arr)-1])
        return memberPublicId

    def testRedis(self):
        try:
            conn = redis.Redis(host='127.0.0.1', port=6379)
            conn.set("test","test")
        except Exception as e:
            self.logger.debug("connecting to Redis -- 127.0.0.1:6379. Connection refused")
            return False
        else:
            self.logger.debug("connecting to Redis -- 127.0.0.1:6379. Connection sucessfully!")
            return True
    pass

    def close(self):
        print("All end.")
    
    def get_logger(self):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__)) #获取当前目录的绝对路径
        today = time.strftime("%Y%m%d", time.localtime())
        filename = '/'+today +'.log'
        log_dir = BASE_DIR + filename
        fh = logging.FileHandler(log_dir,encoding='utf-8') #创建一个文件流并设置编码utf8
        logger = logging.getLogger() #获得一个logger对象，默认是root
        logger.setLevel(logging.DEBUG)  #设置最低等级debug
        fm = logging.Formatter("%(asctime)s --- %(message)s")  #设置日志格式
        logger.addHandler(fh) #把文件流添加进来，流向写入到文件
        fh.setFormatter(fm) #把文件流添加写入格式
        return logger

pass

class InvitationLimitError(Exception):
    def __init__(self,accountName, pageLink):  
        print("the account:{0} cannot invite anyone today. The user page now is {1}".format(accountName,pageLink))
        super().__init__()
    pass
pass

if __name__ == '__main__':
    main()