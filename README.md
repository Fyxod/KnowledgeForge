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

maybe filter out the '\n' in the text chunks before chunking if you get time

update retrieval query prompt, check if it works otherwise remove question + retrieval query concatenation
try generating summaries

also return the chunk, page no, document etc used

test with other documents
Add image parser