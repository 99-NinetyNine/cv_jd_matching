from langchain_google_genai import GoogleGenerativeAIEmbeddings
import dotenv
dotenv.load_dotenv()
em =  GoogleGenerativeAIEmbeddings(model="models/embedding-001", )
 
cv_embedding = em.embed_query("a for apple")
print(cv_embedding)