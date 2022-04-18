import pymysql
import pymysql.cursors

class SQL(object):
    def __init__(self, 
    host, 
    user, 
    password, 
    db, 
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor):
        self.host = host
        self.user = user
        self.password = password
        self.db = db
        self.charset = charset
        self.cursorclass = cursorclass
        self.connection = None
        

    def get_connection(self):
        connection = pymysql.connect(host=self.host,
                                    user=self.user,
                                    password=self.password,
                                    db=self.db,
                                    charset=self.charset,
                                    cursorclass=self.cursorclass)
        self.connection = connection

    def db_get(self, sql, placeholders:tuple=()):
        self.get_connection()
        cursor = self.connection.cursor()
        cursor.execute(sql, placeholders)
        result = []
        for row in cursor:
            result.append(row)
        if cursor.fetchall() == ():
            result = None
        self.connection.close()
        return result

    def query(self, sql, placeholders:tuple=()):
        try:
            self.get_connection()
            cursor = self.connection.cursor()
            cursor.execute(sql, placeholders)
            self.connection.commit()
            self.connection.close()
            return True
        except Exception:
            return False

# sql = nSQL('188.225.47.17', 'user', 'password', 'basename')
# print(sql.db_get("Select uid from conversations_members limit 2"))