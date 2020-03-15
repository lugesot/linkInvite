import json
import redis
import urllib
import os.path
from linkedin_api import Linkedin

reidsClient = redis.Redis(host='127.0.0.1', port=6379)
username = input("please enter accnout name:")
print(username)
password = input("please enter accnout password:")

linkedin = Linkedin(username, password ,refresh_cookies=True)

profileId = input("please enter profileId:")
profile = linkedin.get_profile(profileId)
print("this urn_id:" + profile["profile_id"])
connections = linkedin.get_profile_connections(profile["profile_id"])

sharedConnectionsKey = "sharedConnections"
for index, item in enumerate(connections):
    reidsClient.sadd(sharedConnectionsKey, item['public_id'])
members = reidsClient.smembers(sharedConnectionsKey)
isMember = reidsClient.sismember(sharedConnectionsKey, 'amelie-liu-a11522164')

print("好友已保存，此次用户好友数量：" + str(len(connections)))