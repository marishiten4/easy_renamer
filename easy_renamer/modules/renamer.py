import os
import json
import io
import zipfile
import shutil
import time
import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS
import piexif
from datetime import datetime
import re

class EasyRenamer:
    def __init__(self):
        # Initialize settings in session state if not present
        if 'settings' not in st.session_state:
            # Default settings
            st.session_state.settings = {
                'template_texts': ["新品 正規品", "送料無料", "即決", "即購入OK"],
                'big_words': ["アート", "イラスト", "原画", "絵画", "AI絵画"],
                'small_words': ["風景", "美女", "美人", "廃墟", "SF", "ファンタジー"],
                'metadata_keywords': ["masterpiece", "best quality", "ultra detailed", "8k", "highres"],
                'keyword_mappings': {
                    "masterpiece": ["傑作", "名作"],
                    "best quality": ["最高品質"],
                    "ultra detailed": ["超高詳細"],
                    "8k": ["高解像度"],
                    "highres": ["高解像度"],
                }
            }
            
            # Create output directory if it doesn't exist
            if not os.path.exists('renamed_images'):
                os.mkdir('renamed_images')
        
        # Ensure all required keys exist
        self._ensure_settings_keys()
    
    def _ensure_settings_keys(self):
        """Ensure all required settings keys exist"""
        required_keys = [
            'template_texts', 
            'big_words', 
            'small_words', 
            'metadata_keywords',
            'keyword_mappings'
        ]
        
        for key in required_keys:
            if key not in st.session_state.settings:
                if key == 'keyword_mappings':
                    st.session_state.settings[key] = {}
                else:
                    st.session_state.settings[key] = []
    
    def save_settings(self):
        """Save settings to a JSON file"""
        # Settings are already saved in session state
        pass
    
    def add_word(self, category, word):
        """Add a word to a category"""
        if word and word.strip():
            if word not in st.session_state.settings[category]:
                st.session_state.settings[category].append(word.strip())
                return True
        return False
    
    def add_keyword_mapping(self, keyword, mapped_values):
        """Add a keyword mapping"""
        if keyword and keyword.strip():
            # Split mapped values by comma and strip whitespace
            values = [v.strip() for v in mapped_values.split(',') if v.strip()]
            st.session_state.settings['keyword_mappings'][keyword.strip()] = values
            return True
        return False
    
    def extract_metadata_keywords(self, image_file):
        """
        Extract keywords from image metadata, especially for Stable Diffusion generated images.
        Returns a dictionary with extracted and mapped keywords.
        """
        try:
            # Open the image and prepare to extract metadata
            image = Image.open(image_file)
            
            result = {
                'extracted': [],
                'mapped': []
            }
            
            # Try to extract EXIF data
            exif_data = {}
            try:
                if hasattr(image, '_getexif') and image._getexif():
                    exif_data = {
                        TAGS.get(tag, tag): value
                        for tag, value in image._getexif().items()
                    }
            except Exception as e:
                pass
                
            # Try to extract parameters from image info (for PNG files)
            try:
                if 'parameters' in image.info:
                    params = image.info['parameters']
                    # Extract words from parameters
                    words = re.findall(r'\b\w+\b', params)
                    result['extracted'].extend(words)
            except Exception as e:
                pass
                
            # Try to extract XMP data (used by some AI image generators)
            try:
                if 'XMP' in image.info:
                    xmp_data = image.info['XMP']
                    # Extract words from XMP data
                    words = re.findall(r'\b\w+\b', xmp_data.decode('utf-8', errors='ignore'))
                    result['extracted'].extend(words)
            except Exception as e:
                pass
                
            # Try to extract PNG text chunks (often used by Stable Diffusion)
            try:
                for chunk in image.text.values():
                    # Extract words from each chunk
                    words = re.findall(r'\b\w+\b', chunk)
                    result['extracted'].extend(words)
            except Exception as e:
                pass

            # Filter keywords based on metadata_keywords list
            filtered_keywords = []
            for keyword in st.session_state.settings['metadata_keywords']:
                if keyword in result['extracted']:
                    filtered_keywords.append(keyword)
                    
                    # Add mapped keywords if available
                    if keyword in st.session_state.settings['keyword_mappings']:
                        result['mapped'].extend(st.session_state.settings['keyword_mappings'][keyword])
            
            result['extracted'] = filtered_keywords
            
            # Remove duplicates and sort
            result['extracted'] = sorted(list(set(result['extracted'])))
            result['mapped'] = sorted(list(set(result['mapped'])))
            
            return result
        except Exception as e:
            st.error(f"メタデータの抽出中にエラーが発生しました: {e}")
            return {'extracted': [], 'mapped': []}
    
    def rename_files(self, files, rename_pattern, custom_numbering="{n:02d}", position='suffix'):
        """
        Rename multiple files based on the pattern and create a ZIP archive
        """
        # Create output directory if it doesn't exist
        if not os.path.exists('renamed_images'):
            os.mkdir('renamed_images')
        else:
            # Clean up existing files
            for file in os.listdir('renamed_images'):
                os.remove(os.path.join('renamed_images', file))
        
        results = {}
        
        # Process files
        for i, file in enumerate(files, 1):
            # Create the new filename
            new_name = self._create_filename(rename_pattern, i, custom_numbering, position)
            
            # Get the file extension
            _, ext = os.path.splitext(file.name)
            
            # Ensure the extension is included
            new_filename = f"{new_name}{ext}"
            
            # Save the file with the new name
            try:
                image = Image.open(file)
                save_path = os.path.join('renamed_images', new_filename)
                image.save(save_path)
                
                # Record the result
                results[file.name] = new_filename
            except Exception as e:
                st.error(f"ファイル {file.name} の処理中にエラーが発生しました: {e}")
        
        return results
    
    def _create_filename(self, pattern, number, custom_numbering, position):
        """
        Create a filename with the pattern and number
        """
        try:
            # Format the number according to the custom format
            formatted_number = custom_numbering.format(n=number)
            
            # Add number to the beginning or end based on position
            if position == 'prefix':
                return f"{formatted_number} {pattern}"
            else:  # suffix
                return f"{pattern} {formatted_number}"
        except Exception as e:
            st.error(f"ファイル名の作成中にエラーが発生しました: {e}")
            # Fallback to simple numbering
            return f"{pattern} {number:02d}"
