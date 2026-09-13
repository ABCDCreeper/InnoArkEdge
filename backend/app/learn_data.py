import sqlite3, os, json, time

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "learn.db")

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, description TEXT, cover TEXT,
            category TEXT, video_url TEXT, xp_reward INTEGER DEFAULT 10
        );
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER, title TEXT, video_url TEXT,
            duration INTEGER, order_num INTEGER,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER, question TEXT,
            options TEXT, correct INTEGER,
            order_num INTEGER,
            FOREIGN KEY (lesson_id) REFERENCES lessons(id)
        );
        CREATE TABLE IF NOT EXISTS user_progress (
            user_id TEXT, course_id INTEGER,
            completed_lessons TEXT DEFAULT '',
            xp INTEGER DEFAULT 0, points INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0, last_activity REAL,
            UNIQUE(user_id, course_id)
        );
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, name TEXT, unlocked_at REAL
        );
    """)
    # Seed sample data if empty
    cur = conn.execute("SELECT COUNT(*) FROM courses")
    if cur.fetchone()[0] == 0:
        conn.executescript("""
            INSERT INTO courses (title,description,cover,category,video_url,xp_reward) VALUES
            ('二次函数探秘','从基础到进阶，掌握二次函数的图像与性质','📐','数学','https://www.w3schools.com/html/mov_bbb.mp4',20),
            ('英语单词大冒险','每日一词，轻松记忆3000核心词汇','📖','英语','https://www.w3schools.com/html/mov_bbb.mp4',15),
            ('物理小实验','动手做实验，理解力学原理','⚗️','科学','https://www.w3schools.com/html/mov_bbb.mp4',25),
            ('Scratch编程入门','用积木搭建你的第一个游戏','💻','编程','https://www.w3schools.com/html/mov_bbb.mp4',30),
            ('历史故事会','穿越时空，聆听历史的声音','🏛️','历史','https://www.w3schools.com/html/mov_bbb.mp4',10);
            
            INSERT INTO lessons (course_id,title,video_url,duration,order_num) VALUES
            (1,'什么是二次函数','https://www.w3schools.com/html/mov_bbb.mp4',180,1),
            (1,'二次函数的图像','https://www.w3schools.com/html/mov_bbb.mp4',240,2),
            (2,'每日一词：Hello','https://www.w3schools.com/html/mov_bbb.mp4',120,1),
            (2,'每日一句：自我介绍','https://www.w3schools.com/html/mov_bbb.mp4',150,2),
            (3,'重力实验','https://www.w3schools.com/html/mov_bbb.mp4',200,1),
            (3,'摩擦力实验','https://www.w3schools.com/html/mov_bbb.mp4',180,2),
            (4,'第一个Scratch项目','https://www.w3schools.com/html/mov_bbb.mp4',300,1),
            (4,'动画与交互','https://www.w3schools.com/html/mov_bbb.mp4',360,2);

            INSERT INTO quizzes (lesson_id,question,options,correct,order_num) VALUES
            (1,'二次函数的标准形式是什么？','["y=ax²+bx+c","y=ax+b","y=a/x","y=a^x"]',0,1),
            (1,'二次函数的图像是什么形状？','["直线","抛物线","双曲线","圆形"]',1,2),
            (3,'Hello的意思是？','["再见","你好","谢谢","对不起"]',1,1),
            (5,'地球上的物体下落是因为什么？','["磁力","重力","弹力","浮力"]',1,1);
        """)
    conn.commit()
    return conn

class LearnDB:
    def __init__(self):
        self._conn = init_db()
    
    def get_courses(self):
        return self._conn.execute("SELECT * FROM courses").fetchall()
    
    def get_course(self, cid):
        return self._conn.execute("SELECT * FROM courses WHERE id=?", (cid,)).fetchone()
    
    def get_lessons(self, course_id):
        return self._conn.execute("SELECT * FROM lessons WHERE course_id=? ORDER BY order_num", (course_id,)).fetchall()
    
    def get_lesson(self, lid):
        return self._conn.execute("SELECT * FROM lessons WHERE id=?", (lid,)).fetchone()
    
    def get_quizzes(self, lesson_id):
        return self._conn.execute("SELECT * FROM quizzes WHERE lesson_id=? ORDER BY order_num", (lesson_id,)).fetchall()
    
    def get_progress(self, user_id, course_id=None):
        if course_id:
            return self._conn.execute("SELECT * FROM user_progress WHERE user_id=? AND course_id=?", (user_id, course_id)).fetchone()
        return self._conn.execute("SELECT * FROM user_progress WHERE user_id=?", (user_id,)).fetchall()
    
    def add_xp(self, user_id, xp):
        self._conn.execute("UPDATE user_progress SET xp=xp+?, points=points+?, last_activity=? WHERE user_id=?", (xp, xp, time.time(), user_id))
        self._conn.commit()
        return self._conn.execute("SELECT xp FROM user_progress WHERE user_id=?").fetchone()
    
    def complete_lesson(self, user_id, course_id, lesson_id):
        now = time.time()
        self._conn.execute("""
            INSERT INTO user_progress (user_id, course_id, completed_lessons, xp, points, streak, last_activity)
            VALUES (?,?,?,?,?,1,?)
            ON CONFLICT(user_id,course_id) DO UPDATE SET
                completed_lessons = completed_lessons || ?, 
                xp = xp + 10, points = points + 10,
                last_activity = ?,
                streak = CASE WHEN last_activity > ? THEN streak + 1 ELSE 1 END
        """, (user_id, course_id, lesson_id, 10, 10, now, f",{lesson_id}", now, now - 86400*2))
        self._conn.commit()
    
    def get_achievements(self, user_id):
        return self._conn.execute("SELECT * FROM achievements WHERE user_id=?", (user_id,)).fetchall()
    
    def unlock_achievement(self, user_id, name):
        self._conn.execute("INSERT OR IGNORE INTO achievements (user_id, name, unlocked_at) VALUES (?,?,?)", (user_id, name, time.time()))
        self._conn.commit()