"""
Document Retriever Tool - Provides document search and retrieval capabilities.
"""

import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from sentence_transformers import SentenceTransformer
import numpy as np

@dataclass
class Document:
    """A document in the retrieval system."""
    id: str
    title: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None

@dataclass
class RetrievalResult:
    """Result of a document retrieval query."""
    document: Document
    score: float
    relevance: str  # HIGH, MEDIUM, LOW

class DocumentRetriever:
    """
    Document retrieval tool using semantic search.
    
    Provides RAG (Retrieval-Augmented Generation) capabilities for agents
    to find relevant documents and information.
    """
    
    def __init__(self, db_path: str = "data/documents.db", model_name: str = "all-MiniLM-L6-v2"):
        self.db_path = Path(db_path)
        self.model_name = model_name
        self.model = None
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Ensure the document database exists and create sample data if needed."""
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._create_sample_database()
    
    def _create_sample_database(self):
        """Create a sample document database for demonstrations."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create documents table
        cursor.execute("""
            CREATE TABLE documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                embedding BLOB
            )
        """)
        
        # Sample documents
        sample_docs = [
            {
                "id": "doc_001",
                "title": "Introduction to Machine Learning",
                "content": """
                Machine Learning is a subset of artificial intelligence that enables computers to learn and make decisions from data without being explicitly programmed. It involves algorithms that can identify patterns in data and make predictions or classifications based on those patterns.
                
                Key types of machine learning include:
                1. Supervised Learning: Learning from labeled examples
                2. Unsupervised Learning: Finding patterns in unlabeled data
                3. Reinforcement Learning: Learning through interaction and feedback
                
                Common applications include image recognition, natural language processing, recommendation systems, and predictive analytics.
                """,
                "metadata": {"category": "AI/ML", "difficulty": "beginner", "tags": ["machine learning", "AI", "algorithms"]}
            },
            {
                "id": "doc_002", 
                "title": "Financial Risk Management Principles",
                "content": """
                Financial risk management is the practice of identifying, analyzing, and mitigating financial risks that could negatively impact an organization's capital and earnings. Effective risk management is crucial for maintaining financial stability and achieving business objectives.
                
                Key risk types include:
                1. Market Risk: Risk from changes in market prices
                2. Credit Risk: Risk of counterparty default
                3. Operational Risk: Risk from internal processes and systems
                4. Liquidity Risk: Risk of inability to meet obligations
                
                Risk management strategies include diversification, hedging, insurance, and setting appropriate risk limits.
                """,
                "metadata": {"category": "Finance", "difficulty": "intermediate", "tags": ["risk management", "finance", "investment"]}
            },
            {
                "id": "doc_003",
                "title": "Quantum Computing Fundamentals", 
                "content": """
                Quantum computing represents a revolutionary approach to computation that leverages quantum mechanical phenomena like superposition and entanglement. Unlike classical computers that use bits (0 or 1), quantum computers use quantum bits (qubits) that can exist in multiple states simultaneously.
                
                Key concepts include:
                1. Superposition: Qubits can be in multiple states at once
                2. Entanglement: Qubits can be correlated in ways that classical physics cannot explain
                3. Quantum Gates: Operations that manipulate qubit states
                4. Quantum Algorithms: Specialized algorithms for quantum computers
                
                Potential applications include cryptography, drug discovery, financial modeling, and optimization problems.
                """,
                "metadata": {"category": "Technology", "difficulty": "advanced", "tags": ["quantum computing", "physics", "algorithms"]}
            },
            {
                "id": "doc_004",
                "title": "Customer Service Best Practices",
                "content": """
                Excellent customer service is fundamental to business success and customer retention. It involves understanding customer needs, providing timely and helpful responses, and going above and beyond to ensure customer satisfaction.
                
                Best practices include:
                1. Active Listening: Fully understand customer concerns before responding
                2. Empathy: Show genuine care and understanding for customer situations
                3. Clear Communication: Use simple, jargon-free language
                4. Follow-up: Ensure issues are fully resolved and customers are satisfied
                5. Continuous Improvement: Learn from feedback and improve processes
                
                Technology can enhance customer service through chatbots, CRM systems, and analytics, but human touch remains essential for complex issues.
                """,
                "metadata": {"category": "Business", "difficulty": "beginner", "tags": ["customer service", "communication", "business"]}
            },
            {
                "id": "doc_005",
                "title": "Data Privacy and Security Guidelines",
                "content": """
                Data privacy and security are critical concerns in the digital age. Organizations must protect sensitive information from unauthorized access, use, and disclosure while complying with relevant regulations like GDPR, CCPA, and HIPAA.
                
                Key principles include:
                1. Data Minimization: Collect only necessary data
                2. Purpose Limitation: Use data only for stated purposes
                3. Access Control: Limit access to authorized personnel
                4. Encryption: Protect data in transit and at rest
                5. Regular Audits: Monitor and assess security measures
                
                Privacy by design should be incorporated into all systems and processes from the beginning, not added as an afterthought.
                """,
                "metadata": {"category": "Security", "difficulty": "intermediate", "tags": ["privacy", "security", "compliance", "GDPR"]}
            }
        ]
        
        # Insert sample documents
        for doc in sample_docs:
            cursor.execute("""
                INSERT INTO documents (id, title, content, metadata)
                VALUES (?, ?, ?, ?)
            """, (doc["id"], doc["title"], doc["content"], json.dumps(doc["metadata"])))
        
        conn.commit()
        conn.close()
        
        print(f"Created sample document database at {self.db_path}")
    
    def _get_model(self):
        """Lazy load the sentence transformer model."""
        if self.model is None:
            try:
                self.model = SentenceTransformer(self.model_name)
            except Exception as e:
                print(f"Warning: Could not load sentence transformer model: {e}")
                self.model = None
        return self.model
    
    def add_document(self, document: Document) -> bool:
        """
        Add a document to the retrieval system.
        
        Args:
            document: Document to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate embedding if model is available
            model = self._get_model()
            if model:
                embedding = model.encode(document.content).tolist()
                document.embedding = embedding
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            embedding_blob = json.dumps(document.embedding).encode() if document.embedding else None
            
            cursor.execute("""
                INSERT OR REPLACE INTO documents (id, title, content, metadata, embedding)
                VALUES (?, ?, ?, ?, ?)
            """, (
                document.id,
                document.title, 
                document.content,
                json.dumps(document.metadata),
                embedding_blob
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error adding document: {e}")
            return False
    
    def search(self, query: str, max_results: int = 5, min_score: float = 0.3) -> List[RetrievalResult]:
        """
        Search for relevant documents using semantic similarity.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            min_score: Minimum similarity score threshold
            
        Returns:
            List of RetrievalResult objects
        """
        try:
            model = self._get_model()
            if not model:
                # Fallback to keyword search
                return self._keyword_search(query, max_results)
            
            # Generate query embedding
            query_embedding = model.encode(query)
            
            # Retrieve all documents with embeddings
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, title, content, metadata, embedding FROM documents WHERE embedding IS NOT NULL")
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            
            for row in rows:
                doc_id, title, content, metadata_str, embedding_blob = row
                
                if embedding_blob:
                    doc_embedding = np.array(json.loads(embedding_blob.decode()))
                    
                    # Calculate cosine similarity
                    similarity = np.dot(query_embedding, doc_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
                    )
                    
                    if similarity >= min_score:
                        document = Document(
                            id=doc_id,
                            title=title,
                            content=content,
                            metadata=json.loads(metadata_str),
                            embedding=doc_embedding.tolist()
                        )
                        
                        # Determine relevance level
                        if similarity >= 0.7:
                            relevance = "HIGH"
                        elif similarity >= 0.5:
                            relevance = "MEDIUM"
                        else:
                            relevance = "LOW"
                        
                        results.append(RetrievalResult(
                            document=document,
                            score=float(similarity),
                            relevance=relevance
                        ))
            
            # Sort by score and limit results
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:max_results]
            
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return self._keyword_search(query, max_results)
    
    def _keyword_search(self, query: str, max_results: int) -> List[RetrievalResult]:
        """
        Fallback keyword-based search when semantic search is unavailable.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of RetrievalResult objects
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Simple keyword matching
            search_terms = query.lower().split()
            
            cursor.execute("SELECT id, title, content, metadata FROM documents")
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            
            for row in rows:
                doc_id, title, content, metadata_str = row
                
                # Calculate keyword match score
                content_lower = (title + " " + content).lower()
                matches = sum(1 for term in search_terms if term in content_lower)
                score = matches / len(search_terms) if search_terms else 0
                
                if score > 0:
                    document = Document(
                        id=doc_id,
                        title=title,
                        content=content,
                        metadata=json.loads(metadata_str)
                    )
                    
                    relevance = "HIGH" if score >= 0.7 else "MEDIUM" if score >= 0.3 else "LOW"
                    
                    results.append(RetrievalResult(
                        document=document,
                        score=score,
                        relevance=relevance
                    ))
            
            # Sort by score and limit results
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:max_results]
            
        except Exception as e:
            print(f"Error in keyword search: {e}")
            return []
    
    def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """
        Retrieve a specific document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document if found, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, title, content, metadata, embedding FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                doc_id, title, content, metadata_str, embedding_blob = row
                embedding = None
                if embedding_blob:
                    embedding = json.loads(embedding_blob.decode())
                
                return Document(
                    id=doc_id,
                    title=title,
                    content=content,
                    metadata=json.loads(metadata_str),
                    embedding=embedding
                )
            
            return None
            
        except Exception as e:
            print(f"Error retrieving document: {e}")
            return None
    
    def format_results_for_agent(self, results: List[RetrievalResult], query: str) -> str:
        """
        Format search results for agent consumption.
        
        Args:
            results: Search results to format
            query: Original search query
            
        Returns:
            Formatted string representation
        """
        if not results:
            return f"No relevant documents found for query: '{query}'"
        
        formatted = f"Document Search Results for '{query}' ({len(results)} found):\n\n"
        
        for i, result in enumerate(results, 1):
            doc = result.document
            formatted += f"{i}. **{doc.title}** (Relevance: {result.relevance}, Score: {result.score:.3f})\n"
            formatted += f"   Category: {doc.metadata.get('category', 'Unknown')}\n"
            formatted += f"   Content Preview: {doc.content[:200]}...\n"
            formatted += f"   Document ID: {doc.id}\n\n"
        
        return formatted

# Example usage and testing
def test_document_retriever():
    """Test function for document retriever."""
    retriever = DocumentRetriever()
    
    # Test search
    results = retriever.search("machine learning algorithms", max_results=3)
    formatted = retriever.format_results_for_agent(results, "machine learning algorithms")
    print("Search Test:")
    print(formatted)
    
    # Test specific document retrieval
    doc = retriever.get_document_by_id("doc_001")
    if doc:
        print(f"\nDocument Retrieval Test:")
        print(f"Title: {doc.title}")
        print(f"Content: {doc.content[:200]}...")

if __name__ == "__main__":
    test_document_retriever()