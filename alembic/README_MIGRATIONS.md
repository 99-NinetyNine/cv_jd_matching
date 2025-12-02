# Database Migrations with Alembic

This project uses Alembic for database schema migrations.

## Quick Reference

### Create a new migration
When you make changes to models in `core/db/models.py`, create a migration:
```bash
make migration msg="description of your changes"
# or
alembic revision --autogenerate -m "description of your changes"
```

### Apply migrations
```bash
make migrate
# or
alembic upgrade head
```

### Rollback last migration
```bash
alembic downgrade -1
```

### View migration history
```bash
alembic history
```

### Check current migration version
```bash
alembic current
```

## How It Works

1. **Models**: Define your database schema in `core/db/models.py` using SQLModel
2. **Generate Migration**: Alembic compares your models to the current database and generates a migration script
3. **Review**: Check the generated migration in `alembic/versions/` to ensure it's correct
4. **Apply**: Run the migration to update your database schema

## Important Notes

- Always review auto-generated migrations before applying them
- Test migrations on a development database first
- Migrations are applied in order based on their revision IDs
- The `alembic_version` table in your database tracks which migrations have been applied

## Example Workflow

```bash
# 1. Make changes to core/db/models.py
# 2. Generate migration
make migration msg="add user preferences table"

# 3. Review the generated file in alembic/versions/
# 4. Apply the migration
make migrate
```

## Configuration

- `alembic.ini`: Main Alembic configuration
- `alembic/env.py`: Environment setup, imports your models and database URL
- `alembic/versions/`: Contains all migration scripts
