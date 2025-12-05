# USE_REAL_LLM = True #False
import os
USE_REAL_LLM = os.environ.get("USE_REAL_LLM") == "true"