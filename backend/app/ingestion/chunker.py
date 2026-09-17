import re
from typing import List
from ..models.schema import DocumentChunk

class SmartChunker:
    """
    Header-aware and sliding-window chunker designed for technical runbooks and documentation.
    Preserves error codes, headings, code blocks, and fix instructions together.
    """
    
    @staticmethod
    def chunk_markdown(doc_id: str, doc_title: str, text: str, max_words: int = 500) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        
        # Split by markdown H1/H2 headers so entire problem, root cause, and fix steps stay together
        sections = re.split(r'\n(?=#{1,2}\s+)', text)
        
        chunk_idx = 0
        for sec in sections:
            sec_clean = sec.strip()
            if not sec_clean:
                continue
            
            # Extract section heading
            heading_match = re.match(r'^(#{1,3})\s+(.+)$', sec_clean, re.MULTILINE)
            section_title = heading_match.group(2).strip() if heading_match else "General"
            
            words = sec_clean.split()
            if len(words) <= max_words:
                chunks.append(DocumentChunk(
                    chunk_id=f"{doc_id}_chunk_{chunk_idx}",
                    doc_id=doc_id,
                    doc_title=doc_title,
                    section=section_title,
                    content=sec_clean,
                    token_count=len(words),
                    metadata={"source_doc": doc_id, "heading": section_title}
                ))
                chunk_idx += 1
            else:
                # Sliding window with overlap
                stride = max_words - 50
                for start in range(0, len(words), stride):
                    window = words[start:start + max_words]
                    chunk_text = " ".join(window)
                    chunks.append(DocumentChunk(
                        chunk_id=f"{doc_id}_chunk_{chunk_idx}",
                        doc_id=doc_id,
                        doc_title=doc_title,
                        section=f"{section_title} (part {start // stride + 1})",
                        content=chunk_text,
                        token_count=len(window),
                        metadata={"source_doc": doc_id, "heading": section_title, "part": start // stride + 1}
                    ))
                    chunk_idx += 1
                    if start + max_words >= len(words):
                        break
                        
        return chunks
