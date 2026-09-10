-- 注意：本文件记录的是当前数据库中 users 表的真实结构。
-- 如果表已存在，CREATE TABLE IF NOT EXISTS 会被静默跳过（不报错、也不改结构），
-- 所以改结构请用 ALTER TABLE，或先 DROP TABLE 再重建。

create DATABASE IF NOT EXISTS recruit_quizzes_test_four_database;
USE recruit_quizzes_test_four_database;

SELECT DATABASE();

CREATE TABLE IF NOT EXISTS users (
    userID    INT AUTO_INCREMENT PRIMARY KEY,  -- 主键必须是 userID 单列
    username  VARCHAR(50)  NOT NULL UNIQUE,    -- UNIQUE 让重名由数据库兜底
    password  VARCHAR(255) NOT NULL,
    sessionID VARCHAR(100)                     -- 可空：未登录/已注销时为 NULL
);

-- 如果表已建好但缺 sessionID 列，用这行补：
ALTER TABLE users ADD COLUMN sessionID VARCHAR(100);
