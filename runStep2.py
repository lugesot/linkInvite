import time
import os.path
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import redis

#搜索用户的账号
def main():

    accounts = []
    messageFile = "message.txt"
    accountFile = "accounts.txt"

    si = SendInvitation(accounts)
    if si.testRedis() == True:
        si.readMessage(messageFile)
        si.readAccount(accountFile)
        si.inviteUserList()
        si.close()

#element.close()
class SendInvitation(object):
    def __init__(self,accounts):
        self.accountIndex = -1
        self.connectUserLimit = 200   #每个账户一天最多添加的用户数
        self.reidsClient = redis.Redis(host='127.0.0.1', port=6379)
    
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
            print("linkin账号文件 {0} 不存在".format(fileName))
            raise
        #print(self.accounts)

    def readMessage(self, fileName):
        d = os.getcwd()
        fileName=d +'/'+fileName 
        self.message = ""
        with open(fileName, 'r', encoding="utf-8") as file:
            self.message = file.read()
        print("邀请样式:" + self.message)

    #领英限制：每个账户一天只能邀请100人
    def swichNextUser(self):
        self.accountIndex = self.accountIndex +1
        if self.accountIndex>=len(self.accounts):
            raise Exception("无account可用了，名额都已用尽")
        self.accountName = self.accounts[self.accountIndex][0]

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
        self.driver.implicitly_wait(10)
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
        self.driver.implicitly_wait(10)

        connectBtnXpath = '//main//section//button[contains(@class,"pv-s-profile-actions--connect")]'
        try:
            locator = (By.XPATH, connectBtnXpath)
            WebDriverWait(self.driver, 8, 0.5).until(EC.element_to_be_clickable(locator))
        except TimeoutException as te:
            print("检查是否 是否通过more按钮 connect")
            try:
                moreBtnXpath = '//button[@id="ember66"]'
                locator = (By.XPATH, moreBtnXpath)
                WebDriverWait(self.driver, 2, 0.5).until(EC.element_to_be_clickable(locator))
            except TimeoutException as te2:
                print("超时: " + pageLink)
            else:
                moreBtn = self.driver.find_element_by_xpath(moreBtnXpath)
                moreBtn.click()
                try:
                    connPath = '//main//section//artdeco-dropdown-item[contains(@class,"pv-s-profile-actions--connect")]'
                    locator = (By.XPATH, connPath)
                    WebDriverWait(self.driver, 2, 0.5).until(EC.element_to_be_clickable(locator))
                except TimeoutException as te3:
                    print("已经是好友: " + pageLink)
                else:
                    self.clickConnectBtn(connPath, pageLink)

        except Exception as e:
            print("异常发生："+e)
            print("页面地址："+pageLink)
        else:
            self.clickConnectBtn(connectBtnXpath, pageLink)
        finally:
            self.driver.close()
        pass
    
    def clickConnectBtn(self, btnXPah, pageLink):
        #print("connect btn found")
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
        sendInvitaionBtn.click()
        time.sleep(0.5)
        # 判断是否添加联系用户受限制
        try:
            limitBtn = self.driver.find_element_by_xpath("//button[@data-control-name='fuse_limit_got_it']")
        except NoSuchElementException:
            self.recordResult(self.accountName, pageLink)
            pass
        # 如何limitBtn存在，则抛异常
        raise InvitationLimitError(self.accountName, pageLink)
    
    def checkLimitByRedis(self):
        today = time.strftime("%Y%m%d", time.localtime())
        keyName = self.accountName + today
        if self.reidsClient.exists(keyName):
            if ord(self.reidsClient.get("account20200223"))<=self.connectUserLimit:
                return True
            else:
                return False

        return True
        pass

    def recordResult(self, userName, pageLink):
        today = time.strftime("%Y%m%d", time.localtime())
        keyName = self.accountName + today
        if self.reidsClient.exists(keyName):
            count = ord(self.reidsClient.incr(keyName))
            if count > self.connectUserLimit:
                raise InvitationLimitError(userName, pageLink)
        else:
            self.reidsClient.set(keyName, 1)
        pass
    
    def inviteUserList(self):
        fileName = input("输入用户主页列表txt文件名（不需要后缀）:")
        self.swichNextUser()
        d = os.getcwd()
        fileName=d +'/'+fileName + ".txt"
        try:
            with open(fileName, 'r', encoding="utf-8") as file:
                while True:
                    userMainPageLink = file.readline()
                    if not userMainPageLink: 
                        break
                    userMainPageLink = userMainPageLink.strip()

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
            print("{0}文件不存在".format(fileName))
            raise 
        pass

    def testRedis(self):
        try:
            conn = redis.Redis(host='127.0.0.1', port=6379)
            conn.set("test","test")
        except Exception as e:
            print("connecting to Redis -- 127.0.0.1:6379. Connection refused")
            return False
        else:
            print("connecting to Redis -- 127.0.0.1:6379. Connection sucessfully!")
            return True
    pass

    def close(self):
        print("All end.")

class InvitationLimitError(Exception):
    def __init__(self,accountName, pageLink):  
        print("the account:{0} cannot invite anyone today. The user page now is {1}".format(accountName,pageLink))
        super().__init__()
    pass

if __name__ == '__main__':
    main()