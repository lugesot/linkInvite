import redis
import time
import os.path
import logging,os
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
    if ci.testRedis() == True:
        try:
            ci.logger.debug("搜索页面：" + str(0))
            ci.readAccount(accountFile)
            ci.login()
            #等待页面过滤candidate操作结束
            data = input("please enter any key to store candidate data info to the file: ")
            #列表
            #xpath https://www.cnblogs.com/liangblog/p/11943877.html
            ci.logger.info("开始搜集：")   
        
            ci.searchPage(0)
        except Exception as e:
            print(e)
            ci.logger.error(e)
        else:
            print("搜集完毕")
        ci.logger.info("本次浏览用户数：" + str(ci.browseCount))
        ci.logger.info("本次共搜集个数：" + str(ci.collectUserCount))   

#element.close()
class CollectInfo(object):
    def __init__(self):
        self.logger = self.get_logger()
        options = webdriver.ChromeOptions()
        options.add_argument("--incognito") #隐身模式
        #driver_path = "C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe"  # chromedriver.exe 的路径
        #driver = webdriver.Chrome(executable_path=driver_path, options=options)
        self.driver = webdriver.Chrome(options=options)
        self.reidsClient = redis.Redis(host='127.0.0.1', port=6379)
        self.createFile()
        # 浏览用户计数
        self.browseCount = 0 
        # 搜集目标计数
        self.collectUserCount = 0
        #self.sharedConnectionsKey = "sharedConnections"
        #self.data = []
        

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
            self.logger.debug("{0}文件不存在".format(fileName))
            raise fnf
        pass

    def login(self):
        username = self.accounts[0][0]
        password = self.accounts[0][1]
        time.sleep(0.5)
        self.driver.get("https://www.linkedin.com")
        self.driver.implicitly_wait(8)
        element = self.driver.find_element_by_name("session_key")
        element.send_keys(username)
        element = self.driver.find_element_by_name("session_password")
        element.send_keys(password)
        element.send_keys(Keys.RETURN)

    def searchPage(self,index):
        self.logger.debug("搜索页面：" + str(index))
        self.driver.implicitly_wait(1)
        self.searchWindow = self.driver.window_handles[1] #.current_window_handle()
        self.driver.switch_to.window(self.searchWindow)

        # 当前页面target用户
        #self.userList = self.driver.find_elements_by_xpath("//div[@id='search-results-region']//div[@class='top-card-info']//a")
        userList = self.driver.find_elements_by_xpath("//div[@id='search-results-region']//li[@class='search-result']")
        for idx, item in enumerate(userList):
            viewsBtn = item.find_elements_by_xpath('.//button[contains(text(),"Views")]')
            if len(viewsBtn)==0:
                hrefItems = item.find_elements_by_xpath('.//div[@class="top-card-info"]//a')
                self.profilePage(hrefItems[0])
            # else: view的不添加

        # into next page
        nextPath = "//footer[@id='pagination-region']//div[@class='pagination-container']//li[@class='next']"
        locator = (By.XPATH, nextPath)
        try:
            WebDriverWait(self.driver, 5, 0.5).until(EC.element_to_be_clickable(locator))
        except TimeoutException as te:
            self.logger.debug("all pages end")
        else:
            
            nextP = self.driver.find_elements_by_xpath(nextPath+"//a")
            self.logger.debug("准备点击下一页")
            nextP[0].click()
            self.logger.debug("点击了下一页")
            time.sleep(5)
            self.searchPage(index+1)
    
    def profilePage(self,item):
        self.browseCount = self.browseCount +1
        urlEle = item.get_attribute("href")
        newWindow = "window.open('"+urlEle+"');"
        
        print("处理用户:" + urlEle)
        self.logger.debug("处理用户:" + urlEle)

        self.driver.execute_script(newWindow)
        toHandle = self.driver.window_handles[2]
        self.driver.switch_to.window(toHandle)
        self.driver.implicitly_wait(4)
        locator = (By.XPATH, '//div[@id="primary-content"]//div[@class="module-footer"]//a')
        try:
            WebDriverWait(self.driver, 3, 0.5).until(EC.element_to_be_clickable(locator))
        except TimeoutException as te:
            print("无摘要用户:"+urlEle)
            self.logger.debug("无摘要用户:"+urlEle)
        else:
            profilePage = self.driver.find_element_by_xpath("//div[@id='primary-content']//div[@class='module-footer']//a")
            mainPageUrl = profilePage.get_attribute("href")
            print("添加用户:" + mainPageUrl)
            self.logger.debug("添加用户:" + mainPageUrl)
            # self.data.append({"mainPageUrl":mainPageUrl})
            self.saveData(mainPageUrl)
            self.collectUserCount = self.collectUserCount + 1 
        #profilePage.click()
        self.driver.close()
        self.driver.switch_to.window(self.searchWindow)

    def mainPage(self):
        toHandle = self.driver.window_handles[2]
        self.driver.switch_to.window(toHandle)
        self.driver.implicitly_wait(4)
        locator = (By.XPATH, '//main//section//button')
        WebDriverWait(self.driver, 3, 0.5).until(EC.element_to_be_clickable(locator))
        try:
            self.driver.find_element_by_xpath('//main//section//button[contains(@class,"pv-s-profile-actions--connect")]')
        except Exception as e:
            print(e.message)
            print("connect btn not found")
            self.logger.debug(e)
            self.logger.debug("connect btn not found")
        else:
            print("connect btn found")
            self.logger.debug("connect btn not found")
        self.driver.close()

    def close(self):
        data = input("input any key to end program ")

    def get_logger(self):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__)) #获取当前目录的绝对路径
        today = time.strftime("%Y%m%d", time.localtime())
        filename = '/collect'+today +'.log'
        log_dir = BASE_DIR + filename
        fh = logging.FileHandler(log_dir,encoding='utf-8') #创建一个文件流并设置编码utf8
        logger = logging.getLogger() #获得一个logger对象，默认是root
        logger.setLevel(logging.DEBUG)  #设置最低等级debug
        fm = logging.Formatter("%(asctime)s --- %(message)s")  #设置日志格式
        logger.addHandler(fh) #把文件流添加进来，流向写入到文件
        fh.setFormatter(fm) #把文件流添加写入格式
        return logger
    pass
    #########
    def saveData(self, row):
        with open(self.filename, 'w', encoding="utf-8") as file:
            file.write(row + "\n")
        pass

    def createFile(self):
        today = time.strftime("%Y%m%d", time.localtime())
        d = os.getcwd()
        filename=d +'/'+today +'_'
        index = 1
        while os.path.isfile(filename  + str(index)+ ".txt"):
            index = index + 1

        self.filename = filename + str(index) + ".txt"
        # with open(filename, 'w', encoding="utf-8") as file:
        #     for row in dataList:
        #         file.write(row['mainPageUrl']+"\n")

if __name__ == '__main__':
    # u = Util()
    # row = {'mainPageUrl':'http://baidu.com'}
    # list =[row]
    # list.append(row)
    # u.createFile(list)
    main()