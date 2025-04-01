import streamlit as st

def load_css():
    """Load custom CSS for the application"""
    st.markdown("""
    <style>
    /* Dark theme for performance */
    .stApp {
        background-color: #121212;
        color: #FFFFFF;
    }
    
    /* Improve input field */
    .rename-input-container {
        margin: 15px 0;
        padding: 10px;
        background-color: #212121;
        border-radius: 5px;
        border: 1px solid #4169E1;
    }
    
    /* Custom header styles */
    .custom-header {
        font-size: 1.5rem;
        color: #FFFFFF;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    
    /* Style for inputs */
    input, select, textarea {
        background-color: #333 !important;
        color: white !important;
        border: 1px solid #4169E1 !important;
    }
    
    /* Style for buttons */
    button {
        background-color: #4169E1 !important;
        color: white !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #212121;
        border-radius: 5px;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #FFFFFF;
    }
    
    /* Results area */
    .results-container {
        background-color: #212121 !important;
        color: white !important;
        border: 1px solid #4169E1 !important;
    }
    
    /* Image captions */
    .css-1aehpvj {
        color: #FFFFFF !important;
    }
    
    /* Add style for image selection */
    img.selected {
        border: 3px solid #4169E1;
    }
    
    /* Format preview */
    .format-preview {
        padding: 5px 10px;
        background-color: #333;
        border-radius: 5px;
        margin-top: 5px;
        font-family: monospace;
        color: #FFFFFF;
    }
    
    /* Improve tooltip styling */
    [data-tooltip]:hover::before {
        background-color: #4169E1;
        color: white;
        border-radius: 4px;
        padding: 5px;
    }
    
    /* Image list styles */
    .image-list {
        border: 1px solid #4169E1;
        border-radius: 5px;
        max-height: 400px;
        overflow-y: auto;
        background-color: #212121;
    }
    .image-item {
        padding: 8px;
        margin: 2px;
        cursor: pointer;
        border-bottom: 1px solid #333;
        transition: background-color 0.2s ease;
    }
    .image-item:hover {
        background-color: #333;
    }
    .image-item.selected {
        background-color: #4169E1;
        border-left: 3px solid #1890ff;
    }
    
    /* Word block styles */
    .word-block {
        display: inline-block;
        background-color: #4169E1;
        color: white;
        border: 1px solid #1E90FF;
        border-radius: 5px;
        padding: 5px 10px;
        margin: 5px;
        cursor: pointer;
        font-weight: bold;
        transition: transform 0.1s ease-in-out;
    }
    .word-block:hover {
        transform: scale(1.05