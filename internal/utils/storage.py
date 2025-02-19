import os
from typing import List
from pathlib import Path
import streamlit as st
import streamlit.runtime.uploaded_file_manager
from PyPDF2 import PdfReader
import io


class StorageHandler:
    def __init__(self, base_dir: str = "storage"):
        self.base_dir = base_dir
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)

    def get_course_dir(self, course_id: str | int) -> str:
        """Get the directory path for a specific course."""
        course_dir = os.path.join(self.base_dir, str(course_id))
        Path(course_dir).mkdir(parents=True, exist_ok=True)
        return course_dir

    def save_files(self, course_id: str, files: List[streamlit.runtime.uploaded_file_manager.UploadedFile]) -> List[str]:
        """Save uploaded files to the course directory.

        Args:
            course_id: The ID of the course.
            files: List of uploaded files.

        Returns:
            List of file paths where the files are saved.
        """
        course_dir = self.get_course_dir(course_id)
        saved_file_paths = []

        for file in files:
            # Clean the filename to prevent path traversal
            safe_filename = os.path.basename(file.name)
            file_path = os.path.join(course_dir, safe_filename)
            
            # Determine file type based on extension
            ext = os.path.splitext(safe_filename)[1].lower()
            text_extensions = {'.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv'}
            
            try:
                if ext == '.pdf':
                    # For PDF files, extract text and save both binary and text
                    # Save binary PDF
                    with open(file_path, "wb") as f:
                        f.write(file.getbuffer())
                    
                    # Extract and save text content
                    text_content = self._extract_pdf_text(file)
                    text_file_path = file_path + '.txt'
                    with open(text_file_path, "w", encoding='utf-8') as f:
                        f.write(text_content)
                    saved_file_paths.extend([file_path, text_file_path])
                    
                elif ext in text_extensions:
                    # For text files, decode and save as UTF-8
                    content = file.getvalue().decode('utf-8', errors='replace')
                    with open(file_path, "w", encoding='utf-8') as f:
                        f.write(content)
                    saved_file_paths.append(file_path)
                else:
                    # For other binary files, save as-is
                    with open(file_path, "wb") as f:
                        f.write(file.getbuffer())
                    saved_file_paths.append(file_path)
                    
            except Exception as e:
                st.error(f"Error saving file {safe_filename}: {str(e)}")
                continue
                
        return saved_file_paths

    def _extract_pdf_text(self, file) -> str:
        """Extract text from a PDF file.
        
        Args:
            file: PDF file object
            
        Returns:
            Extracted text content
        """
        try:
            # Create PDF reader object
            pdf_reader = PdfReader(io.BytesIO(file.getvalue()))
            
            # Extract text from all pages
            text_content = []
            for page in pdf_reader.pages:
                text_content.append(page.extract_text())
                
            return "\n\n".join(text_content)
        except Exception as e:
            st.error(f"Error extracting text from PDF: {str(e)}")
            return ""

    def list_files(self, course_id: str) -> List[str]:
        """List all files in the course directory.

        Args:
            course_id: The ID of the course.

        Returns:
            List of file paths in the course directory.
        """
        course_dir = self.get_course_dir(course_id)
        return [os.path.join(course_dir, f) for f in os.listdir(course_dir) if os.path.isfile(os.path.join(course_dir, f))]

    def delete_files(self, course_id: str) -> None:
        """Delete all files in the course directory.

        Args:
            course_id: The ID of the course.
        """
        course_dir = self.get_course_dir(course_id)
        for file in os.listdir(course_dir):
            file_path = os.path.join(course_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)