-- =====================================================================
--  База данных ИС «Инженерные требования и трассируемость»
--  СУБД: MySQL 8.0, кодировка utf8mb4
-- =====================================================================

CREATE DATABASE IF NOT EXISTS reqtrace_admin
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE reqtrace_admin;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS backups;
DROP TABLE IF EXISTS trace_links;
DROP TABLE IF EXISTS requirements;
DROP TABLE IF EXISTS project_members;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS requirement_types;
DROP TABLE IF EXISTS requirement_categories;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- Роли пользователей
-- ---------------------------------------------------------------------
CREATE TABLE roles (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  code        VARCHAR(30)  NOT NULL UNIQUE,
  name        VARCHAR(100) NOT NULL,
  description VARCHAR(255) NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Пользователи системы
-- ---------------------------------------------------------------------
CREATE TABLE users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  login         VARCHAR(50)  NOT NULL UNIQUE,
  full_name     VARCHAR(150) NOT NULL,
  email         VARCHAR(150) NOT NULL UNIQUE,
  position      VARCHAR(120) NULL,
  role_id       INT          NOT NULL,
  is_active     TINYINT(1)   NOT NULL DEFAULT 1,
  password_hash VARCHAR(255) NOT NULL,
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login_at DATETIME     NULL,
  CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES roles(id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  INDEX ix_users_role (role_id),
  INDEX ix_users_active (is_active)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Справочник: категории требований
-- ---------------------------------------------------------------------
CREATE TABLE requirement_categories (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(100) NOT NULL UNIQUE,
  description VARCHAR(255) NULL,
  color       CHAR(7)      NOT NULL DEFAULT '#64748b'
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Справочник: типы требований (уровни декомпозиции)
-- ---------------------------------------------------------------------
CREATE TABLE requirement_types (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  code        VARCHAR(10)  NOT NULL UNIQUE,
  name        VARCHAR(100) NOT NULL UNIQUE,
  level       TINYINT      NOT NULL DEFAULT 1,
  description VARCHAR(255) NULL,
  CONSTRAINT chk_types_level CHECK (level BETWEEN 1 AND 5)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Проекты
-- ---------------------------------------------------------------------
CREATE TABLE projects (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  code        VARCHAR(20)  NOT NULL UNIQUE,
  name        VARCHAR(200) NOT NULL,
  description TEXT         NULL,
  status      ENUM('planning','active','on_hold','closed') NOT NULL DEFAULT 'planning',
  manager_id  INT          NULL,
  start_date  DATE         NULL,
  end_date    DATE         NULL,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_projects_manager FOREIGN KEY (manager_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  INDEX ix_projects_status (status)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Участники проекта и права доступа к проекту
-- ---------------------------------------------------------------------
CREATE TABLE project_members (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  project_id   INT NOT NULL,
  user_id      INT NOT NULL,
  access_level ENUM('read','write','manage') NOT NULL DEFAULT 'read',
  added_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_member UNIQUE (project_id, user_id),
  CONSTRAINT fk_members_project FOREIGN KEY (project_id) REFERENCES projects(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_members_user FOREIGN KEY (user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Требования
-- ---------------------------------------------------------------------
CREATE TABLE requirements (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  project_id  INT          NOT NULL,
  code        VARCHAR(30)  NOT NULL,
  title       VARCHAR(255) NOT NULL,
  description TEXT         NULL,
  category_id INT          NULL,
  type_id     INT          NOT NULL,
  priority    ENUM('low','medium','high','critical') NOT NULL DEFAULT 'medium',
  status      ENUM('draft','review','approved','implemented','verified','rejected')
              NOT NULL DEFAULT 'draft',
  source      VARCHAR(255) NULL,
  author_id   INT          NULL,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_req_code UNIQUE (project_id, code),
  CONSTRAINT fk_req_project  FOREIGN KEY (project_id)  REFERENCES projects(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_req_category FOREIGN KEY (category_id) REFERENCES requirement_categories(id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_req_type     FOREIGN KEY (type_id)     REFERENCES requirement_types(id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_req_author   FOREIGN KEY (author_id)   REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  INDEX ix_req_status (status),
  INDEX ix_req_priority (priority),
  FULLTEXT INDEX ft_req_text (title, description)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Связи трассируемости между требованиями
-- ---------------------------------------------------------------------
CREATE TABLE trace_links (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  source_id  INT NOT NULL,
  target_id  INT NOT NULL,
  link_type  ENUM('derives','refines','satisfies','verifies','depends') NOT NULL DEFAULT 'derives',
  comment    VARCHAR(255) NULL,
  created_by INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_link UNIQUE (source_id, target_id, link_type),
  CONSTRAINT fk_link_source FOREIGN KEY (source_id) REFERENCES requirements(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_link_target FOREIGN KEY (target_id) REFERENCES requirements(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_link_user FOREIGN KEY (created_by) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Резервные копии
-- ---------------------------------------------------------------------
CREATE TABLE backups (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  filename   VARCHAR(255) NOT NULL,
  size_bytes INT          NOT NULL DEFAULT 0,
  tables_cnt INT          NOT NULL DEFAULT 0,
  rows_cnt   INT          NOT NULL DEFAULT 0,
  comment    VARCHAR(255) NULL,
  created_by INT          NULL,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_backup_user FOREIGN KEY (created_by) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Журнал действий администратора
-- ---------------------------------------------------------------------
CREATE TABLE audit_log (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT          NULL,
  action     VARCHAR(20)  NOT NULL,
  entity     VARCHAR(50)  NOT NULL,
  entity_id  INT          NULL,
  details    VARCHAR(500) NULL,
  ip_address VARCHAR(45)  NULL,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  INDEX ix_audit_created (created_at),
  INDEX ix_audit_action (action),
  INDEX ix_audit_entity (entity)
) ENGINE=InnoDB;
