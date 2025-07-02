# Multi-Modal-Enterprise-Knowledge-Synthesis-Platform

use python 3.10


data/
└── users/
    └── user_123/
        ├── uploads/
        │   ├── original_doc1.pdf
        │   └── original_doc2.docx
        ├── parsed/
        │   ├── doc1.json           ← includes image metadata
        │   └── doc2.json
        ├── images/
        │   └── doc1/               ← one folder per document
        │       ├── page_1_img1.png
        │       ├── page_1_img2.png
        │       └── page_3_img1.png
        └── chroma/
            └── index/

[Start]
   ↓
[Document Ingestion (only once per upload)]
   ↓
[User Question Input]
   ↓
[Vector Search 1]
   ↓
[LLM Answer + Grade Confidence]
   ↓
[Check if Confident]
   ├─> Yes → [Return Answer]
   ↓ No
[Rephrase Question]
   ↓
[Vector Search 2 (Rephrased)]
   ↓
[LLM Answer + Grade Confidence Again]
   ↓
[Check if Confident]
   ├─> Yes → [Return Answer]
   ↓ No
[Web Search]
   ↓
[Final LLM Answer]
   ↓
[Return Answer]

Yet to initialize graph