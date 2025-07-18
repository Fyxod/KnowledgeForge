# Multi-Modal-Enterprise-Knowledge-Synthesis-Platform

#  use docker 

```bash
docker build -t what-ever-u-name-it .
```

```bash

docker run -it \
           --env-file .env \
           --dns=8.8.8.8 \
           -p 3000:8080 \
         -p 8000:8000\
       -v $(pwd)d/data:/data \
           what-ever-u-name-it
```

pass .env and attach a volume to store data from chromadb



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

to use it 
 
 install py 3.10
 create env


 run backend - uvicorn app.main:app
 run frontend - npm i && npm run dev 









Next steps:
add route to get chat history for a single thread (or maybe just preload it in the frontend)
Whole frontend

customize error messages too like success messages

--index-url https://download.pytorch.org/whl/cu121
torch
torchvision
torchaudio

pip3 install -U xformers --index-url https://download.pytorch.org/whl/cu128

maybe filter out the '\n' in the text chunks before chunking if you get time

try generating summaries

also return the chunk, page no, document etc used

test with other documents
Add image parser

link parser in input along with docs