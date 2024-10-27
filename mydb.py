import mysql.connector

dataBase = mysql.connector.connect(
    host = 'localhost',
    user = 'root',
    passwd = 'Ajmal@c120',
    
)

#prepare a cursor object

cursorObject = dataBase.cursor()

#create a database
cursorObject.execute("CREATE DATABASE my_database")

print('ALL DONE!')