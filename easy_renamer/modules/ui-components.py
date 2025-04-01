import streamlit as st
import io
from PIL import Image
import base64

def load_css():
    """
    Load custom CSS styles for the application
    """
    css = """
    <style>
        /* Main container styling */
        .main .block-container {
            padding-top: 2rem;
        }
        
        /* Word blocks styling */
        .word-blocks-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 15px;
        }
        
        .word-block {
            background-color: #f0f2f6;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 6px 10px;
            margin: 4px;
            cursor: pointer;
            display: inline-block;
            font-size: 0.9rem;
            transition: all 0.2s;
        }
        
        .word-block:hover {
            background-color: #e0e2e6;
            transform: translateY(-2px);
        }
        
        .word-block.template {
            background-color: #e8f4f9;
            border-color: #a8d1e8;
        }
        
        .word-block.big {
            background-color: #f9e8e8;
            border-color: #e8a8a8;
        }
        
        .word-block.small {
            background-color: #e8f9e8;
            border-color: #a8e8a8;
        }
        
        .word-block.meta {
            background-color: #f9f9e8;
            border-color: #e8e8a8;
        }
        
        /* Custom header styling */
        .custom-header {
            font-size: 1.2rem;
            font-weight: bold;
            margin: 20px 0 10px 0;
            color: #555;
        }
        
        /* Rename input container */
        .rename-input-container {
            margin: 15px 0;
        }
        
        /* Image list styling */
        .image-list {
            border: 1px solid #ddd;
            border-radius: 4px;
            max-height: 400px;
            overflow-y: auto;
            background-color: #f9f9f9;
        }
        
        .image-list-item {
            padding: 8px 10px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .image-list-item:hover {
            background-color: #e0e0e0;
        }
        
        .image-list-item.selected {
            background-color: #d0e8ff;
        }
        
        /* Format preview */
        .format-preview {
            padding: 10px;
            background-color: #f5f5f5;
            border-radius: 4px;
            margin: 10px 0;
            font-family: monospace;
        }
    </style>
    """
    
    # Add JavaScript for word blocks functionality
    js = """
    <script>
        // Function to initialize word blocks functionality
        function initWordBlocks() {
            const wordBlocks = document.querySelectorAll('.word-block');
            const inputField = document.querySelector('input[key="rename_input_field"]');
            
            if (!wordBlocks.length || !inputField) {
                // Try again in 500ms if elements are not found
                setTimeout(initWordBlocks, 500);
                return;
            }
            
            wordBlocks.forEach(block => {
                // Click handler
                block.addEventListener('click', function() {
                    const word = this.getAttribute('data-word');
                    const cursorPos = inputField.selectionStart;
                    const currentValue = inputField.value;
                    
                    // Insert the word at cursor position
                    const newValue = currentValue.substring(0, cursorPos) + word + currentValue.substring(cursorPos);
                    
                    // Update input value
                    inputField.value = newValue;
                    
                    // Update Streamlit's internal state
                    const event = new Event('input', { bubbles: true });
                    inputField.dispatchEvent(event);
                    
                    // Set cursor position after inserted word
                    inputField.focus();
                    inputField.setSelectionRange(cursorPos + word.length, cursorPos + word.length);
                });
                
                // Drag functionality
                block.setAttribute('draggable', 'true');
                
                block.addEventListener('dragstart', function(e) {
                    e.dataTransfer.setData('text/plain', this.getAttribute('data-word'));
                });
            });
            
            // Set up drag-and-drop for input field
            inputField.addEventListener('dragover', function(e) {
                e.preventDefault();
            });
