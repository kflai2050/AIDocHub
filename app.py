import os
import streamlit as st
import pandas as pd
from PIL import Image
from backend import LocalVectorStore, DocumentProcessor, generate_groq_answer, UPLOAD_DIR



# Set page config
st.set_page_config(
    page_title="AI Document & Vector Assistant",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom premium styling injection
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Plus+Jakarta+Sans:wght@300;400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    
    /* Main container background */
    .stApp {
        background: linear-gradient(135deg, #0f0c1b 0%, #15102a 50%, #06020f 100%);
        color: #e2e8f0;
    }
    
    /* Sleek glowing header */
    .glow-header {
        font-size: 2.8rem;
        background: linear-gradient(90deg, #a855f7 0%, #ec4899 50%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: left;
        margin-bottom: 0.2rem;
        font-weight: 800;
    }
    
    .subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Premium glassmorphic cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.5rem;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        margin-bottom: 1.5rem;
    }
    
    /* Highlight/neon badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 50px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    
    .badge-pdf { background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-txt { background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-docx { background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-excel { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-image { background-color: rgba(139, 92, 246, 0.15); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.3); }
    
    /* File container styling */
    .file-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 1rem;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 12px;
        margin-bottom: 0.5rem;
        transition: all 0.2s ease-in-out;
    }
    .file-row:hover {
        background: rgba(255, 255, 255, 0.05);
        border-color: rgba(168, 85, 247, 0.3);
        transform: translateY(-1px);
    }
    
    /* Source chunk highlights */
    .source-chunk {
        border-left: 3px solid #a855f7;
        background: rgba(168, 85, 247, 0.03);
        padding: 0.75rem 1rem;
        margin-bottom: 0.75rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.9rem;
    }
    
    .score-badge {
        float: right;
        background: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        padding: 0.1rem 0.4rem;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 700;
    }
    
    /* Sidebar custom styling */
    .css-1d391tw, [data-testid="stSidebar"] {
        background-color: #0c0817;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    </style>
""", unsafe_allow_html=True)

# Initialize vector store session state
if "vector_store" not in st.session_state:
    st.session_state.vector_store = LocalVectorStore()

if "uploaded_files_registry" not in st.session_state:
    st.session_state.uploaded_files_registry = []

# Title Area
st.markdown('<div class="glow-header">AI Document Intelligence Hub</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Upload multi-format documents, inspect details inline, and perform semantic search instantly.</div>', unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.markdown("## ⚙️ Model Configuration")
    
    api_provider = st.selectbox(
        "AI Agent Synthesis Engine",
        options=["Groq API (llama-3.3-70b-versatile)", "Local Offline (No API Key)"],
        index=0
    )
    
    groq_key = ""
    if api_provider == "Groq API (llama-3.3-70b-versatile)":
        groq_key = st.text_input(
            "Groq API Key",
            value="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",
            type="password",
            help="Enter your Groq API key to enable synthesization."
        )
        if not groq_key:
            st.warning("Please provide a Groq API Key to enable AI Agent synthesization.")
            
    st.markdown("---")
    st.markdown("## 🧹 Actions")
    if st.button("Reset Database & Uploads", use_container_width=True):
        st.session_state.vector_store.reset_db()
        # Clean local folder files
        if os.path.exists(UPLOAD_DIR):
            for f in os.listdir(UPLOAD_DIR):
                try:
                    os.remove(os.path.join(UPLOAD_DIR, f))
                except Exception:
                    pass
        st.session_state.uploaded_files_registry = []
        st.success("Database and upload folders successfully reset!")
        st.rerun()

# Layout splits
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown('<div class="glass-card"><h3>📥 Upload Documents</h3>', unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "Drag & drop or browse files",
        type=["txt", "pdf", "docx", "xls", "xlsx", "png", "jpg", "jpeg", "gif", "webp"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
                    
    # Detect if any previously indexed files from the uploader widget were removed
    current_uploaded_names = [f.name for f in uploaded_files] if uploaded_files else []
    registry_files_to_remove = [
        reg_doc for reg_doc in st.session_state.uploaded_files_registry 
        if reg_doc.get("source") == "uploader" and reg_doc["filename"] not in current_uploaded_names
    ]
    if registry_files_to_remove:
        for doc_to_remove in registry_files_to_remove:
            # 1. Delete from ChromaDB
            st.session_state.vector_store.delete_document(doc_to_remove["filename"])
            # 2. Delete from local disk
            try:
                if os.path.exists(doc_to_remove["path"]):
                    os.remove(doc_to_remove["path"])
            except Exception:
                pass
            # 3. Remove from session registry
            st.session_state.uploaded_files_registry = [
                r for r in st.session_state.uploaded_files_registry 
                if r["file_id"] != doc_to_remove["file_id"]
            ]
            st.toast(f"Removed and de-indexed {doc_to_remove['filename']}", icon="🗑️")
        st.rerun()
        
    if uploaded_files:
        pending_files = [f for f in uploaded_files if not any(r["filename"] == f.name for r in st.session_state.uploaded_files_registry)]
        
        if pending_files:
            # If the user has cancelled, show hold warning with options to resume or clear
            if st.session_state.get("indexing_cancelled", False):
                st.warning("⚠️ Indexing was cancelled by the user.")
                col_resume, col_clear = st.columns(2)
                with col_resume:
                    if st.button("⚙️ Resume Indexing", use_container_width=True):
                        st.session_state.indexing_cancelled = False
                        st.rerun()
                with col_clear:
                    if st.button("🧹 Reset/Clear Uploads", use_container_width=True):
                        st.session_state.indexing_cancelled = False
                        st.session_state.uploaded_files_registry = []
                        st.session_state.vector_store.reset_db()
                        # Clean local folder files
                        if os.path.exists(UPLOAD_DIR):
                            for f in os.listdir(UPLOAD_DIR):
                                try:
                                    os.remove(os.path.join(UPLOAD_DIR, f))
                                except Exception:
                                    pass
                        st.success("Queue and database cleared! Please remove files from uploader widget.")
                        st.rerun()
            else:
                # Automatically start processing!
                progress_text = st.empty()
                p_bar = st.progress(0.0)
                
                # Show cancellation button
                if st.button("🚫 Cancel Processing", key="cancel_proc_btn", use_container_width=True):
                    st.session_state.indexing_cancelled = True
                    st.toast("Cancellation requested. Stopping...", icon="⚠️")
                    st.rerun()
                
                for idx, uploaded_file in enumerate(pending_files):
                    progress_text.text(f"Processing ({idx+1}/{len(pending_files)}): {uploaded_file.name}...")
                    p_bar.progress(idx / len(pending_files))
                    
                    file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                        
                    ext = os.path.splitext(uploaded_file.name)[1].lower()
                    file_type = ext.replace(".", "").upper()
                    
                    # Process file
                    result = DocumentProcessor.process_file(file_path, file_type, api_key=groq_key)
                    
                    # Store to database
                    file_id = f"doc_{len(st.session_state.uploaded_files_registry)}_{int(pd.Timestamp.now().timestamp())}"
                    st.session_state.vector_store.add_document(
                        file_id=file_id,
                        content=result["content"],
                        doc_metadata=result["metadata"]
                    )
                    
                    # Add to registry
                    st.session_state.uploaded_files_registry.append({
                        "file_id": file_id,
                        "filename": uploaded_file.name,
                        "type": file_type,
                        "path": file_path,
                        "content_preview": result["content"][:2000],
                        "source": "uploader"
                    })
                    
                p_bar.progress(1.0)
                progress_text.text("Indexing complete!")
                st.toast("All pending documents indexed successfully!", icon="✅")
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Document Registry and Preview
    st.markdown('<div class="glass-card"><h3>📂 Document Library</h3>', unsafe_allow_html=True)
    
    if not st.session_state.uploaded_files_registry:
        st.info("No documents uploaded yet. Drag or browse files to get started!")
    else:
        for doc in st.session_state.uploaded_files_registry:
            badge_class = f"badge-{doc['type'].lower()}"
            if doc['type'] in ["XLS", "XLSX"]:
                badge_class = "badge-excel"
            elif doc['type'] in ["JPG", "JPEG", "PNG", "GIF", "WEBP"]:
                badge_class = "badge-image"
                
            st.markdown(f"""
                <div class="file-row">
                    <div>
                        <span class="badge {badge_class}">{doc['type']}</span>
                        <strong>{doc['filename']}</strong>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Action buttons for document
            col_preview, col_download, col_delete = st.columns(3)
            with col_preview:
                if st.button("🔍 Preview", key=f"preview_{doc['file_id']}", use_container_width=True):
                    st.session_state.preview_doc = doc
            with col_download:
                try:
                    with open(doc["path"], "rb") as f:
                        st.download_button(
                            label="📥 Download",
                            data=f.read(),
                            file_name=os.path.basename(doc["filename"]),
                            key=f"download_{doc['file_id']}",
                            use_container_width=True
                        )
                except Exception:
                    st.error("Error downloading file.")
            with col_delete:
                if st.button("🗑️ Delete", key=f"delete_{doc['file_id']}", use_container_width=True):
                    # 1. Delete from ChromaDB
                    st.session_state.vector_store.delete_document(doc["filename"])
                    # 2. Delete from local disk
                    try:
                        if os.path.exists(doc["path"]):
                            os.remove(doc["path"])
                    except Exception:
                        pass
                    # 3. Remove from session registry
                    st.session_state.uploaded_files_registry = [
                        r for r in st.session_state.uploaded_files_registry if r["file_id"] != doc["file_id"]
                    ]
                    # Also clear preview if active
                    if "preview_doc" in st.session_state and st.session_state.preview_doc["file_id"] == doc["file_id"]:
                        del st.session_state.preview_doc
                    st.toast(f"Removed and de-indexed {doc['filename']}", icon="🗑️")
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Preview Area below the registry
    if "preview_doc" in st.session_state:
        p_doc = st.session_state.preview_doc
        st.markdown(f'<div class="glass-card"><h3>🔍 Inline Preview: {p_doc["filename"]}</h3>', unsafe_allow_html=True)
        
        ext = os.path.splitext(p_doc["filename"])[1].lower()
        if ext == ".txt":
            st.text_area("File Content", p_doc["content_preview"], height=300, disabled=True)
        elif ext == ".pdf":
            st.text_area("Parsed Text Content", p_doc["content_preview"], height=300, disabled=True)
        elif ext == ".docx":
            st.text_area("Parsed Document Content", p_doc["content_preview"], height=300, disabled=True)
        elif ext in [".xls", ".xlsx"]:
            try:
                xls = pd.ExcelFile(p_doc["path"])
                sheet = st.selectbox("Select Sheet", xls.sheet_names)
                df = pd.read_excel(xls, sheet_name=sheet)
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Error loading Excel sheet: {e}")
        elif ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
            try:
                img = Image.open(p_doc["path"])
                st.image(img, caption=p_doc["filename"], use_container_width=True)
                st.write(p_doc["content_preview"])
            except Exception as e:
                st.error(f"Error loading Image: {e}")
                
        if st.button("Close Preview", key="close_preview", use_container_width=True):
            del st.session_state.preview_doc
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="glass-card"><h3>💬 Ask Your Documents</h3>', unsafe_allow_html=True)
    
    with st.form("query_form", clear_on_submit=False):
        query = st.text_input("Enter your natural language query:", placeholder="e.g. What is the total revenue in the sheet? or What is the mark in Maths?")
        submit_button = st.form_submit_button("🚀 Submit Query", use_container_width=True)
    
    if query and submit_button:
        # Step-by-step Progress Bar
        progress_bar = st.progress(0, text="Initializing request...")
        
        # 1. Search Database
        progress_bar.progress(25, text="Querying ChromaDB vector database...")
        search_results = st.session_state.vector_store.search(query, n_results=5)
        
        if not search_results:
            progress_bar.progress(100, text="Complete.")
            st.warning("No relevant details found matching your query in the database.")
        else:
            # 2. Synthesis
            progress_bar.progress(60, text="Synthesizing response via Groq (llama-3.3-70b-versatile)...")
            if api_provider == "Groq API (llama-3.3-70b-versatile)" and groq_key:
                answer = generate_groq_answer(groq_key, query, search_results)
            else:
                top_match = search_results[0]
                answer = f"**[Offline Mode] Best Match from {top_match['metadata']['filename']}:**\n\n{top_match['document']}\n\n*Configure a Groq API Key in the sidebar to get full conversational summaries.*"
            
            # 3. Done
            progress_bar.progress(100, text="Synthesized successfully!")
            
            # Render answer
            st.markdown("#### 🤖 Agent Response")
            st.info(answer)
            
            # Show source passages
            with st.expander("📚 Retrieved Source Chunks (ChromaDB Similarity)", expanded=True):
                for idx, chunk in enumerate(search_results):
                    score_pct = f"{int(chunk['score'] * 100)}%" if 'score' in chunk and chunk['score'] <= 1.0 else f"Match Rank: {chunk.get('score', 1)}"
                    st.markdown(f"""
                        <div class="source-chunk">
                            <span class="score-badge">{score_pct} Similarity</span>
                            <strong>File:</strong> {chunk['metadata']['filename']} (Chunk {chunk['metadata'].get('chunk_index', 0)})<br/>
                            <div style="margin-top: 0.5rem; color: #cbd5e1;">{chunk['document']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                        
    st.markdown('</div>', unsafe_allow_html=True)
