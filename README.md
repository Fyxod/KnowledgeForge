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
Save chat history in query route and call agent there
add auth middleware in the required routes
add route to get chat hstory for a single thread (or maybe just preload it in the frontend)
Whole frontend
