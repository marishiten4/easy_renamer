import os
import json
import re
from PIL import Image
from PIL.ExifTags import TAGS
from concurrent.futures import ThreadPoolExecutor
import streamlit as st

class EasyRenamer:
    def __init__(self):
        # Initialize session state
        if 'settings' not in st.session_state:
            self.load_settings()
        
        if 'image_cache' not in st.session_state:
            st.session_state.image_cache = {}
            
        if 'metadata_cache' not in st.session_state:
            st.session_state.metadata_cache = {}
            
        if 'extracted_keywords' not in st.session_state:
            st.session_state.extracted_keywords = []
        
        # AI image metadata keywords
        self.ai_image_keywords = [
            'Stable Diffusion', 'Prompt', 'Negative prompt', 
            'Steps', 'CFG scale', 'Seed', 'Model', 
            'Characters', 'Style', 'Emotion'
        ]

    def load_settings(self):
        """Load settings file"""
        default_settings = {
            'template_texts': ['出品画像', 'カードゲーム用', 'コレクション'],
            'big_words': ['キャラクター', '美少女', 'アニメ'],
            'small_words': ['可愛い', '人気', '高品質'],
            'registered_words': [],
            'metadata_keywords': [],
            'keyword_mappings': {
                'Stable Diffusion': ['AI生成', 'デジタル'],
                'anime': ['アニメ', '漫画風'],
                'character': ['キャラクター', '人物'],
                'portrait': ['ポートレート', '肖像画'],
                'landscape': ['風景', '自然']
            }
        }
        
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                st.session_state.settings = json.load(f)
                # Ensure keyword_mappings exists in loaded settings
                if 'keyword_mappings' not in st.session_state.settings:
                    st.session_state.settings['keyword_mappings'] = default_settings['keyword_mappings']
        except FileNotFoundError:
            st.session_state.settings = default_settings

    def save_settings(self):
        """Save settings file"""
        try:
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(st.session_state.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            st.error(f"設定の保存中にエラーが発生: {e}")

    def extract_metadata_keywords(self, image_file):
        """Extract metadata keywords from image with caching support"""
        # Check if metadata is already cached
        if image_file.name in st.session_state.metadata_cache:
            return st.session_state.metadata_cache[image_file.name]
        
        keywords = []
        mapped_keywords = []
        try:
            # Reset file pointer to beginning (important for uploaded files)
            image_file.seek(0)
            
            # Convert to PIL Image object
            image = Image.open(image_file)
            
            # Try to extract parameters from image info
            param_str = ""
            if 'parameters' in image.info:
                param_str = image.info['parameters']
            elif 'comment' in image.info:
                param_str = image.info['comment']
            elif hasattr(image, '_getexif') and image._getexif():
                exif = {TAGS.get(k, k): v for k, v in image._getexif().items() if k in TAGS}
                if 'UserComment' in exif:
                    param_str = str(exif['UserComment'])
                elif 'ImageDescription' in exif:
                    param_str = str(exif['ImageDescription'])
            
            # Convert bytes to string if needed
            if isinstance(param_str, bytes):
                try:
                    param_str = param_str.decode('utf-8', errors='ignore')
                except:
                    param_str = str(param_str)
            
            if param_str:
                # Search for AI keywords
                for keyword in self.ai_image_keywords:
                    if keyword.lower() in param_str.lower():
                        keywords.append(keyword)
                
                # Extract custom keywords - look for words and phrases
                prompt_match = re.findall(r'\b[A-Za-z0-9]+\b', param_str.lower())
                keywords.extend(prompt_match[:10])  # Add first 10 keywords
                
                # Look for Japanese words (hiragana, katakana, kanji)
                ja_words = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+', param_str)
                keywords.extend(ja_words[:5])  # Add first 5 Japanese keywords
                
                # Get mapped keywords from settings
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower in st.session_state.settings['keyword_mappings']:
                        mapped_keywords.extend(st.session_state.settings['keyword_mappings'][keyword_lower])
                    
                    # Also check for partial matches
                    for mapping_key in st.session_state.settings['keyword_mappings']:
                        if mapping_key.lower() in keyword_lower or keyword_lower in mapping_key.lower():
                            mapped_keywords.extend(st.session_state.settings['keyword_mappings'][mapping_key])
        
        except Exception as e:
            st.warning(f"メタデータの抽出中にエラーが発生: {str(e)}")
        
        # Cache the results
        unique_keywords = list(set(keywords))  # Remove duplicates
        unique_mapped = list(set(mapped_keywords))  # Remove duplicates
        
        result = {
            'extracted': unique_keywords,
            'mapped': unique_mapped
        }
        
        st.session_state.metadata_cache[image_file.name] = result
        return result

    def rename_files(self, files, base_name, custom_numbering, number_position):
        """
        Rename files with custom numbering
        
        :param files: List of uploaded files
        :param base_name: Base rename name
        :param custom_numbering: Custom numbering format
        :param number_position: Position of numbering (prefix or suffix)
        :return: Dictionary of rename results
        """
        results = {}
        output_dir = 'renamed_images'
        
        # Create output directory if not exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Process files with a thread pool for better performance
        def process_file(idx_file):
            idx, uploaded_file = idx_file
            # Generate custom filename with user-defined numbering
            file_ext = os.path.splitext(uploaded_file.name)[1]
            
            # Replace placeholders in custom numbering
            try:
                number_str = custom_numbering.format(n=idx)
            except Exception as e:
                number_str = str(idx)  # Fallback to simple numbering
            
            # Determine filename based on number position
            if number_position == 'prefix':
                new_filename = f"{number_str}_{base_name}{file_ext}"
            else:  # suffix
                new_filename = f"{base_name}_{number_str}{file_ext}"
            
            new_filepath = os.path.join(output_dir, new_filename)
            
            try:
                # Reset file position to beginning
                uploaded_file.seek(0)
                
                # Save file
                with open(new_filepath, "wb") as f:
                    f.write(uploaded_file.getvalue())
                return (uploaded_file.name, new_filename)
            except Exception as e:
                return (uploaded_file.name, f"エラー: {str(e)}")
        
        # Use ThreadPoolExecutor to process files in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            file_results = executor.map(process_file, enumerate(files, start=1))
            
        # Convert results to dictionary
        for original, new_name in file_results:
            results[original] = new_name
            
        return results

    def add_word(self, word_type, word):
        """Add a new word to the specified word list"""
        if word and word not in st.session_state.settings[word_type]:
            st.session_state.settings[word_type].append(word)
            self.save_settings()
            st.success(f"ワード '{word}' を{word_type}に追加しました")
        elif word in st.session_state.settings[word_type]:
            st.warning(f"ワード '{word}' は既に存在します")
            
    def add_keyword_mapping(self, keyword, mapped_words):
        """Add a new keyword mapping"""
        if not keyword:
            return False
            
        # Split the mapped words by comma
        mapped_list = [word.strip() for word in mapped_words.split(',') if word.strip()]
        
        # Add or update the mapping
        if keyword.lower() not in st.session_state.settings['keyword_mappings']:
            st.session_state.settings['keyword_mappings'][keyword.lower()] = mapped_list
        else:
            # Update existing mapping
            st.session_state.settings['keyword_mappings'][keyword.lower()] = mapped_list
            
        self.save_settings()
        return True
