import time
import os.path
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
#搜索用户的账号
def main():

    accounts = []
    messageFile = "message.txt"
    accountFile = "accounts.txt"

    si = SendInvitation(accounts)
    si.readMessage(messageFile)
    si.readAccount(accountFile)
    si.inviteUserList()
    si.close()

#element.close()
class SendInvitation(object):
    def __init__(self,accounts):
        self.accountIndex = 0
    
    #format username password\n
    def readAccount(self, fileName):
        self.accounts = []
        d = os.getcwd()
        fileName=d +'/'+fileName 
        self.message = ""
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
            print("{0}文件不存在".format(fileName))
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
        if self.accountIndex>=len(self.accounts):
            raise Exception("无account可用了，名额都已用尽")
        username = self.accounts[self.accountIndex][0]
        password = self.accounts[self.accountIndex][1]
        self.accountIndex = self.accountIndex +1
        options = webdriver.ChromeOptions()
        options.add_argument("--incognito") #隐身模式
        #driver_path = "C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe"  # chromedriver.exe 的路径
        #driver = webdriver.Chrome(executable_path=driver_path, options=options)
        self.driver = webdriver.Chrome(options=options)
        time.sleep(0.5)
        self.driver.get("https://www.linkedin.com")
        self.driver.implicitly_wait(10)
        element = self.driver.find_element_by_name("session_key")
        element.send_keys(username)
        element = self.driver.find_element_by_name("session_password")
        element.send_keys(password)
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
            WebDriverWait(self.driver, 10, 0.5).until(EC.element_to_be_clickable(locator))
        except TimeoutException as te:
            print("页面显示超时，可能已联系过："+pageLink)
        except Exception as e:
            print("异常发生："+e)
        else:
            #print("connect btn found")
            connectBtn = self.driver.find_element_by_xpath(connectBtnXpath)
            connectBtn.click()
            time.sleep(2)
            addNoteBtn = self.driver.find_element_by_xpath("//button[@aria-label='Add a note']")
            addNoteBtn.click()
            time.sleep(0.5)
            note = self.driver.find_element_by_xpath("//textarea[@id='custom-message']")
            note.send_keys(self.message)
            sendInvitaionBtn = self.driver.find_element_by_xpath("//button[@aria-label='Send invitation']")
            sendInvitaionBtn.click()
        finally:
            self.driver.close()
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
                            break
                        except InvitationLimitError as e:   
                            self.swichNextUser()
                            continue
        except FileNotFoundError as fnf:
            print("{0}文件不存在".format(fileName))
        pass

    def close(self):
        print("All end.")


class InvitationLimitError(Exception):
    def __init__(self,accountName):  
        print("the account:{0} cannot invite anyone today.".format(accountName))
        super().__init__()
    pass

if __name__ == '__main__':
    main()