from openai import api_key
from smolagents import Tool
from typing import List, Optional
import os
from pathlib import Path
import pickle
from langchain.docstore.document import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from internal.utils.storage import StorageHandler
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging

logger = logging.getLogger(__name__)

# Get OpenAI API key from environment
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

class RetrieverTool(Tool):
    name = "retriever"
    description = """
    Retrieves relevant content from the uploaded course materials to help generate the course outline.
    Use this tool to find specific information about topics, concepts, and learning materials that should be included in the course.
    """
    inputs = {
        "query": {
            "type": "string",
            "description": "The search query to find relevant content. Be specific about what information you need for the course outline.",
        }
    }
    output_type = "string"

    @classmethod
    def from_course_id(cls, course_id: str) -> 'RetrieverTool':
        """Create a RetrieverTool instance from a course ID.
        
        Args:
            course_id: The ID of the course to create the retriever for
            
        Returns:
            RetrieverTool instance
        """
        storage = StorageHandler()
        
        # Try to load existing vector store first
        instance = cls(docs=[], course_id=course_id)
        vector_store = instance._load_vector_store(course_id)
        if vector_store:
            instance.vector_store = vector_store
            instance.k = 5
            instance.score_threshold = 0.7
            return instance
            
        # If no vector store exists, process the documents
        file_paths = storage.list_files(course_id)
        source_docs = []
        
        for file_path in file_paths:
            try:
                # First try UTF-8
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # If UTF-8 fails, try with latin-1
                    with open(file_path, "r", encoding="latin-1") as f:
                        content = f.read()

                # Skip empty content
                if not content.strip():
                    logger.info(f"Skipping empty file: {file_path}")
                    continue

                # Create document with metadata
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": os.path.basename(file_path),
                        "file_path": file_path,
                    },
                )
                source_docs.append(doc)
                logger.info(f"Successfully processed file: {file_path}")
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")
                continue

        if not source_docs:
            logger.warning("No documents were successfully processed")
            return cls(docs=[], course_id=course_id)

        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            add_start_index=True,
            strip_whitespace=True,
            separators=["\n\n", "\n", ".", " ", ""],
        )

        docs_processed = text_splitter.split_documents(source_docs)
        return cls(docs=docs_processed, course_id=course_id)

    def __init__(self, docs: List[Document], course_id: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        if not docs and not course_id:
            raise ValueError("Either docs or course_id must be provided")
            
        try:
            # Initialize storage handler and default values
            self.storage = StorageHandler()
            self.course_id = course_id
            self.vector_store = None
            self.k = 5  # Number of results to return
            self.score_threshold = 0.7  # Minimum similarity score threshold
            
            # Filter out non-text documents and empty documents
            valid_docs = []
            for doc in docs:
                if doc.page_content and isinstance(doc.page_content, str):
                    # Clean up the text content
                    cleaned_content = self._clean_text(doc.page_content)
                    if cleaned_content:
                        doc.page_content = cleaned_content
                        valid_docs.append(doc)
            
            if not valid_docs and not course_id:
                raise ValueError("No valid text content found in documents")
                
            # Initialize OpenAI embeddings
            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",  # Using the latest embedding model
                dimensions=1536,  # Optimal dimension for text-embedding-3-small
                api_key=OPENAI_API_KEY
            )
            
            # Create FAISS vector store from documents if we have valid docs
            if valid_docs:
                self.vector_store = FAISS.from_documents(
                    valid_docs,
                    embeddings,
                )
                
                # Save vector store if course_id is provided
                if course_id:
                    self._save_vector_store(course_id)
            
        except Exception as e:
            raise ValueError(f"Failed to initialize retriever: {str(e)}")

    def _get_vector_store_path(self, course_id: str) -> str:
        """Get the path where the vector store should be saved for a course."""
        course_dir = self.storage.get_course_dir(course_id)
        return os.path.join(course_dir, "vector_store.faiss")

    def _save_vector_store(self, course_id: str) -> None:
        """Save the FAISS vector store to disk."""
        try:
            vector_store_path = self._get_vector_store_path(course_id)
            self.vector_store.save_local(vector_store_path)
        except Exception as e:
            print(f"Warning: Failed to save vector store: {str(e)}")

    def _load_vector_store(self, course_id: str) -> FAISS | None:
        """Load the FAISS vector store from disk if it exists."""
        try:
            vector_store_path = self._get_vector_store_path(course_id)
            if os.path.exists(vector_store_path):
                embeddings = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    dimensions=1536,
                    api_key=OPENAI_API_KEY
                )
                # Since we're loading from our own saved files in a controlled environment,
                # it's safe to allow deserialization
                return FAISS.load_local(
                    vector_store_path,
                    embeddings,
                    allow_dangerous_deserialization=True
                )
        except Exception as e:
            logger.error(f"Warning: Failed to load vector store: {str(e)}")
        return None

    def _clean_text(self, text: str) -> str:
        """Clean up text content by removing common PDF artifacts and normalizing whitespace.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text content
        """
        if not text:
            return ""
            
        # Remove common PDF artifacts
        artifacts = [
            "endstream", "endobj", "stream", "obj",
            r"\(", r"\)", r"\[", r"\]",
            "xref", "trailer", "startxref"
        ]
        
        cleaned = text
        for artifact in artifacts:
            cleaned = cleaned.replace(artifact, "")
            
        # Normalize whitespace
        cleaned = " ".join(cleaned.split())
        
        return cleaned.strip()

    def forward(self, query: str) -> str:
        """
        Retrieve relevant content from the documents based on the query using semantic search.
        
        Args:
            query: The search query string
            
        Returns:
            A formatted string containing the retrieved content
        """
        if not query or not isinstance(query, str):
            return "Error: Invalid query provided. Please provide a valid search query."

        if not self.vector_store:
            return "No document content available for searching. Please ensure documents have been properly loaded."

        try:
            # Perform similarity search with scores
            docs_and_scores = self.vector_store.similarity_search_with_score(
                query,
                k=self.k
            )
            
            if not docs_and_scores:
                return "No relevant content found in the provided materials."
                
            # Format the results in a more structured way
            result_parts = []
            for i, (doc, score) in enumerate(docs_and_scores, 1):
                # Skip results below threshold
                if score < self.score_threshold:
                    continue
                    
                source = doc.metadata.get('source', 'Unknown source')
                content = doc.page_content.strip()
                if content:
                    # Include relevance score in the output
                    result_parts.append(
                        f"\n=== Relevant Content {i} (from {source}, relevance: {score:.2f}) ===\n"
                        f"{content}\n"
                    )
            
            if not result_parts:
                return "No sufficiently relevant content found in the retrieved documents."
                
            return "\nRelevant course materials:\n" + "\n".join(result_parts)
            
        except Exception as e:
            logger.error(f"Error during retrieval: {str(e)}")
            return f"Error during retrieval: {str(e)}"
