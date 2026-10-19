
CREATE DATABASE IF NOT EXISTS pathpilot;
USE pathpilot;

CREATE TABLE students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    branch VARCHAR(50),
    year INT,
    role ENUM('student', 'admin') DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE skills (
    skill_id INT AUTO_INCREMENT PRIMARY KEY,
    skill_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE student_skills (
    student_id INT,
    skill_id INT,
    proficiency VARCHAR(30) DEFAULT 'Beginner',
    PRIMARY KEY (student_id, skill_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);

CREATE TABLE opportunities (
    opportunity_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    company VARCHAR(100) NOT NULL,
    description TEXT,
    stipend VARCHAR(50),
    application_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE opportunity_skills (
    opportunity_id INT,
    skill_id INT,
    PRIMARY KEY (opportunity_id, skill_id),
    FOREIGN KEY (opportunity_id)
        REFERENCES opportunities(opportunity_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);

CREATE TABLE applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    opportunity_id INT NOT NULL,
    status VARCHAR(30) DEFAULT 'Applied',
    applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (student_id, opportunity_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (opportunity_id)
        REFERENCES opportunities(opportunity_id)
);

INSERT IGNORE INTO skills (skill_name) VALUES
('Java'),
('C'),
('Python'),
('SQL'),
('HTML'),
('CSS'),
('JavaScript'),
('MySQL'),
('Data Structures'),
('Flask');

INSERT INTO opportunities
(title, company, description, stipend, application_url)
VALUES
('Java Intern', 'Demo Company',
 'Learn Java programming and backend development.',
 '8000 per month', 'https://example.com'),
('Web Development Intern', 'Demo Company',
 'Practice HTML, CSS and JavaScript.',
 '6000 per month', 'https://example.com'),
('Python Intern', 'Demo Company',
 'Learn Python programming and databases.',
 '7000 per month', 'https://example.com');
