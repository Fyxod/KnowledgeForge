# Multi-Modal-Enterprise-Knowledge-Synthesis-Platform

use python 3.10

```
data/
└── users/
    └── user_123/
        ├── uploads/
        │   ├── original_doc1.pdf
        │   └── original_doc2.docx
        ├── parsed/
        │   ├── doc1.json
        │   └── doc2.json
        ├── images/
        │   └── doc1/
        │       ├── page_1_img1.png
        │       ├── page_1_img2.png
        │       └── page_3_img1.png
        └── chroma/
            └── index/
```

Next steps:
add route to get chat history for a single thread (or maybe just preload it in the frontend)
Whole frontend

customize error messages too like success messages

--index-url https://download.pytorch.org/whl/cu121
torch
torchvision
torchaudio

pip3 install -U xformers --index-url https://download.pytorch.org/whl/cu128


pip install faiss-cpu not working on my laptop due to cuda version mismatch. Will see if there will be performance issues later, then might use faiss-gpu on gpu server

maybe filter out the '\n' in the text chunks before chunking if you get time

query.py almost fully debugged

def get_recent_history(full_history, turns=2):
    # full_history = list of dicts with 'role' and 'content'
    return full_history[-turns*2:]

update chat history to only contains last n turns of conversation

update retrieval query prompt, check if it works otherwise remove question + retrieval query concatenation
try generating summaries