from pathlib import Path
from typing import Dict, Any, List
import io

class DocumentLoader:
    @staticmethod
    def load_file(file_path: Path) -> Dict[str, Any]:
        """Loads a single file (MD, TXT, or PDF) and returns content and metadata."""
        ext = file_path.suffix.lower()
        doc_id = file_path.stem
        
        if ext in [".md", ".txt", ".log"]:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            # First line as title if markdown
            lines = content.splitlines()
            title = lines[0].replace("#", "").strip() if lines and lines[0].startswith("#") else file_path.name
            return {
                "doc_id": doc_id,
                "title": title,
                "file_name": file_path.name,
                "content": content,
                "type": ext[1:]
            }
        elif ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(file_path))
                text_parts = []
                for i, page in enumerate(reader.pages):
                    extracted = page.extract_text() or ""
                    text_parts.append(f"\n## Page {i + 1}\n{extracted}")
                content = "\n".join(text_parts)
                return {
                    "doc_id": doc_id,
                    "title": file_path.name,
                    "file_name": file_path.name,
                    "content": content,
                    "type": "pdf"
                }
            except Exception as e:
                return {
                    "doc_id": doc_id,
                    "title": file_path.name,
                    "file_name": file_path.name,
                    "content": f"Failed to extract PDF: {str(e)}",
                    "type": "pdf_error"
                }
        else:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            return {
                "doc_id": doc_id,
                "title": file_path.name,
                "file_name": file_path.name,
                "content": content,
                "type": "unknown"
            }

    @staticmethod
    def load_directory(dir_path: Path) -> List[Dict[str, Any]]:
        docs = []
        if not dir_path.exists():
            return docs
        for p in dir_path.glob("*.*"):
            if p.suffix.lower() in [".md", ".txt", ".pdf", ".log"]:
                docs.append(DocumentLoader.load_file(p))
        return docs
