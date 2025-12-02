from sqlmodel import create_engine, SQLModel, Session
import os

# Default to localhost if not set (for dev)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cv_matching")

engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
def destroy_db_and_tables():
    SQLModel.metadata.drop_all(engine)
