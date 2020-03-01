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
    accountFile = "accounts.txt"

    ci = CollectInfo()
    ci.readAccount(accountFile)
    ci.login()
    #等待页面过滤candidate操作结束
    data = input("please enter any key to store candidate data info to the file: ")
    #列表
    #xpath https://www.cnblogs.com/liangblog/p/11943877.html
    ci.searchPage(0)
    #进入个人profile主页
    #ci.profilePage()
    #进入个人主页
    #ci.mainPage()
    #end
    #ci.close()
    ci.save()

#element.close()
class CollectInfo(object):
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--incognito") #隐身模式
        #driver_path = "C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe"  # chromedriver.exe 的路径
        #driver = webdriver.Chrome(executable_path=driver_path, options=options)
        self.driver = webdriver.Chrome(options=options)
        self.data = []
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
        pass

    def login(self):
        username = self.accounts[0][0]
        password = self.accounts[0][1]
        time.sleep(0.5)
        self.driver.get("https://www.linkedin.com")
        self.driver.implicitly_wait(10)
        element = self.driver.find_element_by_name("session_key")
        element.send_keys(username)
        element = self.driver.find_element_by_name("session_password")
        element.send_keys(password)
        element.send_keys(Keys.RETURN)

    def searchPage(self,index):
        self.driver.implicitly_wait(1)
        self.searchWindow = self.driver.window_handles[1] #.current_window_handle()
        self.driver.switch_to.window(self.searchWindow)

        self.userList = self.driver.find_elements_by_xpath("//div[@id='search-results-region']//div[@class='top-card-info']//a")
        for idx, j in enumerate(self.userList):
            self.profilePage(idx)

        # into next page
        nextPath = "//footer[@id='pagination-region']//div[@class='pagination-container']//li[@class='next']"
        locator = (By.XPATH, nextPath)
        try:
            WebDriverWait(self.driver, 5, 0.5).until(EC.element_to_be_clickable(locator))
        except TimeoutException as te:
            print("all pages end")
        else:
            nextP = self.driver.find_elements_by_xpath(nextPath+"//a")
            nextP[0].click()
            time.sleep(5)
            self.searchPage(index+1)
    
    def profilePage(self,index):
        urlEle = self.userList[index].get_attribute("href")
        newWindow = "window.open('"+urlEle+"');"
        self.driver.execute_script(newWindow)
        toHandle = self.driver.window_handles[2]
        self.driver.switch_to.window(toHandle)
        self.driver.implicitly_wait(10)
        locator = (By.XPATH, '//div[@id="primary-content"]//div[@class="module-footer"]//a')
        try:
            WebDriverWait(self.driver, 5, 0.5).until(EC.element_to_be_clickable(locator))
        except TimeoutException as te:
            print("skip who has no profile")
        else:
            profilePage = self.driver.find_element_by_xpath("//div[@id='primary-content']//div[@class='module-footer']//a")
            mainPageUrl = profilePage.get_attribute("href")
            print(mainPageUrl)
            self.data.append({"mainPageUrl":mainPageUrl})
        #profilePage.click()
        self.driver.close()
        self.driver.switch_to.window(self.searchWindow)

    def mainPage(self):
        toHandle = self.driver.window_handles[2]
        self.driver.switch_to.window(toHandle)
        self.driver.implicitly_wait(10)
        locator = (By.XPATH, '//main//section//button')
        WebDriverWait(self.driver, 20, 0.5).until(EC.element_to_be_clickable(locator))
        try:
            self.driver.find_element_by_xpath('//main//section//button[contains(@class,"pv-s-profile-actions--connect")]')
        except Exception as e:
            print(e)
            print("connect btn not found")
        else:
            print("connect btn found")
        self.driver.close()
    def close(self):
        data = input("input any key to end program ")

    def save(self):
        u = Util()
        u.createFile(self.data)
    #########
class Util(object):
    def createFile(self, dataList):
        today = time.strftime("%Y%m%d", time.localtime())
        d = os.getcwd()
        filename=d +'/'+today +'_'
        index = 1
        while os.path.isfile(filename  + str(index)+ ".txt"):
            index = index + 1

        filename = filename + str(index) + ".txt"
        with open(filename, 'w', encoding="utf-8") as file:
            for row in dataList:
                file.write(row['mainPageUrl']+"\n")

if __name__ == '__main__':
    # u = Util()
    # row = {'mainPageUrl':'http://baidu.com'}
    # list =[row]
    # list.append(row)
    # u.createFile(list)
    main()