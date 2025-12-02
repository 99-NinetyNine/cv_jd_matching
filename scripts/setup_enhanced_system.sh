#!/bin/bash
# Setup script for enhanced CV-Job matching system

set -e  # Exit on error

echo "🚀 Setting up Enhanced CV-Job Matching System..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Install Python dependencies
echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
pip install -r requirements_enhanced.txt

# 2. Download spaCy model
echo -e "${YELLOW}📚 Downloading spaCy language model...${NC}"
python -m spacy download en_core_web_sm

# 3. Check PostgreSQL connection
echo -e "${YELLOW}🔍 Checking PostgreSQL connection...${NC}"
if psql -U postgres -d cv_matching -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL connection successful${NC}"
else
    echo -e "${YELLOW}⚠️  PostgreSQL connection failed. Please ensure:${NC}"
    echo "   - PostgreSQL is running"
    echo "   - Database 'cv_matching' exists"
    echo "   - Connection credentials are correct"
fi

# 4. Apply database indices
echo -e "${YELLOW}🗄️  Applying database indices...${NC}"
if [ -f "infra/init_db.sql" ]; then
    psql -U postgres -d cv_matching -f infra/init_db.sql > /dev/null 2>&1
    echo -e "${GREEN}✅ Database indices applied${NC}"
else
    echo -e "${YELLOW}⚠️  infra/init_db.sql not found${NC}"
fi

# 5. Check Redis connection (for Celery)
echo -e "${YELLOW}🔍 Checking Redis connection...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis connection successful${NC}"
else
    echo -e "${YELLOW}⚠️  Redis connection failed. Start Redis with: redis-server${NC}"
fi

# 6. Create necessary directories
echo -e "${YELLOW}📁 Creating directories...${NC}"
mkdir -p uploads
mkdir -p logs
mkdir -p data/test_cvs
echo -e "${GREEN}✅ Directories created${NC}"

# 7. Generate test data (optional)
echo -e "${YELLOW}🎲 Generate test data? (y/n)${NC}"
read -r generate_data
if [ "$generate_data" = "y" ]; then
    echo -e "${YELLOW}Generating 100 CVs and 50 jobs...${NC}"
    python scripts/generate_dummy_cvs.py --cvs 100 --jobs 50
    echo -e "${GREEN}✅ Test data generated${NC}"
fi

# 8. Print next steps
echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Start the API server:"
echo "   uvicorn main:app --reload --port 8000"
echo ""
echo "2. Start Celery worker (in another terminal):"
echo "   celery -A core.worker.celery_app worker --loglevel=info"
echo ""
echo "3. Test the system:"
echo "   curl http://localhost:8000/api/admin/system_health"
echo ""
echo "4. Run load tests:"
echo "   locust -f scripts/locust_load_test.py --host=http://localhost:8000"
echo ""
echo "5. View documentation:"
echo "   cat IMPLEMENTATION_NOTES.md"
echo ""
echo -e "${GREEN}Happy coding! 🎉${NC}"
