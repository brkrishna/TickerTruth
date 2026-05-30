# Dolt Workflow Guide

## 1. Import Schema

### Initial schema import
```bash
cd dolt/
dolt sql < schema.sql
```

### View imported tables
```bash
dolt ls
```

### Inspect specific table structure
```bash
dolt schema show dim_corporate_action_type
```

### Inspect specific table structure
```bash
dolt schema show dim_corporate_action_type
```

### View all schema
```bash
dolt schema show
```

## 2. Commit Changes

### Stage and commit schema changes
```bash
# See what changed
dolt status
```

```bash
# Add all changes
dolt add .
```

```bash
# Commit with message
dolt commit -m "Initial schema creation"
```

### Commit specific table changes
```bash
dolt add dim_corporate_action_type
dolt commit -m "Add corporate action type dimension"
```

### View pending uncommitted changes
```bash
dolt diff
```

### See changes for specific table
```bash
dolt diff dim_corporate_action_type
```

## 3. Inspect History

### View commit log
```bash
dolt log
```

### View commits with details
```bash
dolt log --online
```

### See what changed in a specific commit
```bash
dolt show <commit-hash>
```

### View full diff for a commit
```bash
dolt log -p <commit-hash>
```

### Track changes to a specific table across commits
```bash
dolt log dim_corporate_action_type
```

### View complete table diff between commits
```bash
dolt diff <commit1> <commit2> dim_corporate_action_type
```

### View current working directory changes
```bash
dolt diff HEAD
```

### View data changes (not just schema)
```bash
dolt diff --data dim_corporate_action_type
```

## 4. Common Workflows

### Add seed data and commit
```bash
dolt sql < seed_corporate_actions.sql
dolt add dim_corporate_action_type
dolt commit -m "Add corporate action type seed data"
```

### Drop and recreate tables
```bash
dolt sql < drop_tables.sql
dolt sql < schema.sql
dolt add .
dolt commit -m "Reset schema"
```
### View history of schema modifications
```bash
dolt log --oneline -- schema.sql
```

### Rollback to previous state
```bash
dolt reset --hard <commit-hash>
```

### Check current branch
```bash
dolt branch
```

### Create a feature branch
```bash
dolt branch feature/new-schema
dolt checkout feature/new-schema
```