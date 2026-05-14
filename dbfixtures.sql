-- Sample books for local development.
-- Usage: psql -h "$APP_DB_HOST" -U "$APP_DB_USER" -d "$APP_DB_NAME" -f dbfixtures.sql

INSERT INTO books (title, author, year, isbn)
VALUES
    ('Clean Code',
     'Robert C. Martin',
     2008,
     '9780132350884'),

    ('The Pragmatic Programmer',
     'Andrew Hunt; David Thomas',
     1999,
     '9780201616224'),

    ('Designing Data-Intensive Applications',
     'Martin Kleppmann',
     2017,
     '9781449373320'),

    ('Refactoring: Improving the Design of Existing Code',
     'Martin Fowler',
     1999,
     '9780201485677'),

    ('Test-Driven Development: By Example',
     'Kent Beck',
     2002,
     '9780321146533')
ON CONFLICT (isbn) DO NOTHING;
