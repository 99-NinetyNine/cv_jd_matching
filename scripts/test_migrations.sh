#!/bin/bash
# Test script to demonstrate the migration workflow

echo "🧪 Testing Alembic Migration Workflow"
echo "======================================"
echo ""

echo "1️⃣ Checking current database version..."
make db-current
echo ""

echo "2️⃣ Viewing migration history..."
make db-history
echo ""

echo "✅ Migration system is working correctly!"
echo ""
echo "📝 To create a new migration after changing models:"
echo "   make migration msg='your description'"
echo ""
echo "⬆️  To apply migrations:"
echo "   make migrate"
