import pymysql.cursors
import os

'''
with open("secrets/user") as f:
    user = f.read()[:-1]

with open("secrets/password") as f:
    password = f.read()[:-1]

with open("secrets/database") as f:
    db = f.read()[:-1]
'''

user = os.environ["DBUSER"]
password = os.environ["DBPASSWORD"]
db = os.environ["DBNAME"]

def connection():
    conn = pymysql.connect(host='localhost',
                           user=user,
                           password=password,
                           db=db,
                           charset='utf8mb4',
                           cursorclass=pymysql.cursors.DictCursor)

    c = conn.cursor()

    return c, conn
