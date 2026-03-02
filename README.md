# AiVault
AiVault with .NET Gateway and Local Python Brain

Problem: Not being able to utilise AI when processing sensitive data.
Solution: Have a local brain that processes a PDF document.

1. Gateway
Role: It's the only part of the system that the browser talks to. It handles the traffic.
Action: When you upload a file, the raw bytes from the PDF itself are wrapped in a secure request, forwarding to the python brain.
Why: In a real-world example this would have authentication and logging here to protect th AI from malicious use.

2. The Brain
This is the brain of the project, it waits for the gateway to give it some work. It handles two main job; Ingestion and Retrieval.
Part A: Storing and Indexing
When a PDF from the gateway arrives, the brain follows the pipeline:
    1. Storage: It saves a physical copy of the PDF into the uploads folder.
    2. Parsing: It uses PyPDFLoader to "rip" the text out of the pages.
    3. Chunking: AI cannot read a 50-paged document all at once. The brain slices the text into s,all, overlapping snippets of about 1,000 caracters each.
4. Embedding: This is the ,agic. It sends each chunk through a ,athematical model (all-MiniLM-L6-v2). This turns words into vectors - long lists of numbers that represent themwaning of the text.

3. The Vault
This is your database, it stores the vectors.
Role: It saves those meaningful numbers into the db_vault_free folder on your disk.
The Map: Think of it like a 3D map of idead. Chunks about "Refund POlicies" are stored geographically near chunks about "Money" and "Returns".

4. The Intelligence (Chosen AI model/LLM)
For a free developing version I installed Ollama which is locally ran but this should work if you have paid for OpenAI and have the OPENAI_API_KEY stored as an system variable.