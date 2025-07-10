"""
Simplified Traffic Safety Analyzer - Streamlit App

A simplified web interface that works with test_data images and labels.
Users can click images or upload images to get AI safety reminders with voice.
"""

import streamlit as st
import json
import os
import base64
from pathlib import Path
import random
import time
from dotenv import load_dotenv
load_dotenv()

# Import functions from the main script
import sys
sys.path.append('.')

# Load traffic analysis functions
def load_traffic_functions():
    """Load traffic analysis functions from the main script"""
    import importlib.util
    
    spec = importlib.util.spec_from_file_location("traffic_module", "4-traffic-safety.py")
    traffic_module = importlib.util.module_from_spec(spec)
    
    # Temporarily replace sys.argv to prevent argparse from running
    original_argv = sys.argv
    sys.argv = ['streamlit_simple.py']
    
    try:
        spec.loader.exec_module(traffic_module)
    finally:
        sys.argv = original_argv
    
    return traffic_module

# Load the traffic analysis functions
traffic_module = load_traffic_functions()
analyze_with_ai = traffic_module.analyze_with_ai
text_to_speech = traffic_module.text_to_speech

# Constants
TEST_DATA_DIR = Path("test_data")
IMAGES_DIR = TEST_DATA_DIR / "images"
LABELS_DIR = TEST_DATA_DIR / "labels"
DEFAULT_CSV = "3_aggregation.csv"

# Voice options
VOICE_OPTIONS = {
    "English": {
        "en-US-AriaNeural": "Aria (Female)",
        "en-US-DavisNeural": "Davis (Male)", 
        "en-US-GuyNeural": "Guy (Male)",
        "en-US-JennyNeural": "Jenny (Female)",
        "en-US-JasonNeural": "Jason (Male)",
        "en-US-NancyNeural": "Nancy (Female)"
    },
    "Chinese": {
        "zh-CN-XiaoxiaoNeural": "Xiaoxiao (Female)",
        "zh-CN-YunxiNeural": "Yunxi (Male)",
        "zh-CN-YunjianNeural": "Yunjian (Male)",
        "zh-CN-XiaoyiNeural": "Xiaoyi (Female)",
        "zh-CN-YunyangNeural": "Yunyang (Male)"
    },
    "Korean": {
        "ko-KR-SunHiNeural": "SunHi (Female)",
        "ko-KR-InJoonNeural": "InJoon (Male)",
        "ko-KR-BongJinNeural": "BongJin (Male)",
        "ko-KR-GookMinNeural": "GookMin (Male)",
        "ko-KR-YuJinNeural": "YuJin (Female)"
    },
    "Japanese": {
        "ja-JP-NanamiNeural": "Nanami (Female)",
        "ja-JP-KeitaNeural": "Keita (Male)",
        "ja-JP-AoiNeural": "Aoi (Female)",
        "ja-JP-DaichiNeural": "Daichi (Male)",
        "ja-JP-MayuNeural": "Mayu (Female)"
    }
}

# Language codes mapping
LANGUAGE_CODES = {
    "English": "en-US",
    "Chinese": "zh-CN", 
    "Korean": "ko-KR",
    "Japanese": "ja-JP"
}

def load_css():
    """Load custom CSS styling"""
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton > button {
        background: #f8f9fa !important;
        border: 1px solid #dee2e6 !important;
        padding: 8px 12px !important;
        margin-bottom: 8px !important;
        border-radius: 6px !important;
    }
    .stButton > button:hover {
        background: #e9ecef !important;
        border: 1px solid #007bff !important;
    }
    .safety-reminder {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .config-panel {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

def stop_all_audio():
    """Stop all audio elements in the DOM"""
    audio_stop_script = """
    <script>
    // Function to stop all audio immediately
    function stopAllAudio() {
        const audioElements = document.querySelectorAll('audio');
        audioElements.forEach(function(audio) {
            try {
                audio.pause();
                audio.currentTime = 0;
                // Don't remove or clear src - just pause
            } catch (e) {
                console.log('Error stopping audio:', e);
            }
        });
    }
    
    // Execute immediately
    stopAllAudio();
    </script>
    """
    st.markdown(audio_stop_script, unsafe_allow_html=True)

def clear_audio_cache():
    """Clear all audio-related session state"""
    keys_to_remove = []
    for key in st.session_state.keys():
        if any(prefix in key for prefix in ['analysis_', 'current_analysis_', 'processed_', 'audio_']):
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del st.session_state[key]

def get_available_images():
    """Get list of available test images"""
    if not IMAGES_DIR.exists():
        return []
    
    images = []
    for img_file in IMAGES_DIR.glob("*.jpg"):
        # Check if corresponding label exists
        label_file = LABELS_DIR / f"{img_file.stem}_label.json"
        if label_file.exists():
            images.append({
                'filename': img_file.name,
                'path': str(img_file),
                'label_path': str(label_file)
            })
    
    return sorted(images, key=lambda x: x['filename'])

def load_label_data(label_path):
    """Load label data from JSON file"""
    try:
        with open(label_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading label data: {e}")
        return None

def get_image_base64(image_path):
    """Convert image to base64 string for HTML embedding"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        print(f"Error converting image to base64: {e}")
        return ""

def get_language_prompt(language_choice):
    """Get appropriate language instruction for AI prompt"""
    language_prompts = {
        "English": "Response in English",
        "Chinese": "Response in Chinese",
        "Korean": "Response in Korean", 
        "Japanese": "Response in Japanese"
    }
    return language_prompts.get(language_choice, "Response in English")

def analyze_with_ai_multilingual(label_data, csv_file, language_choice):
    """Enhanced AI analysis with language-specific prompts"""
    if not label_data:
        return None
    
    # Import the necessary modules to modify the prompt
    from openai import AzureOpenAI
    import os
    
    if not os.getenv('AZURE_OPENAI_API_KEY'):
        # Fallback to basic analysis
        return traffic_module.analyze_traffic(label_data, csv_file)['safety_reminder']
    
    try:
        # Get comprehensive analysis with statistical context
        analysis = traffic_module.analyze_traffic(label_data, csv_file)
        
        # Build statistical context for AI prompt
        statistical_context = []
        for category, data in analysis['statistical_analysis'].items():
            context_line = (f"{category}: {data['current_count']} detected "
                          f"(historical avg: {data['historical_avg']:.1f}, "
                          f"level: {data['level_description']}, "
                          f"percentile: {data['percentile_position']})")
            statistical_context.append(context_line)
        
        env = analysis['environment']
        
        # Create data-rich prompt for AI with language specification
        client = AzureOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version='2024-12-01-preview'
        )
        
        language_instruction = get_language_prompt(language_choice)
        
        prompt = f"""
Generate a precise traffic safety reminder (25-40 words) based on this analysis:

ENVIRONMENT:
- Weather: {env['weather']}
- Time: {env['time']}
- Scene: {env['scene']}

STATISTICAL ANALYSIS:
{chr(10).join(statistical_context)}

INSTRUCTIONS:
- Use the statistical comparison to assess risk level
- If any category is "above_normal" or "below_normal", mention it specifically
- Prioritize weather conditions if hazardous
- Provide actionable driving advice
- Keep response short, concise and professional (10-20 words)
- {language_instruction}
- Don't include statistics result in the message

Respond with safety reminder only.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a traffic safety analyst who uses statistical data to provide precise driving recommendations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=60,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"AI analysis failed: {e}")
        # Fallback to basic analysis
        result = traffic_module.analyze_traffic(label_data, csv_file)
        return result['safety_reminder']

def generate_audio_base64(text, language_code, voice_name):
    """Generate audio and return base64 encoded string"""
    import tempfile
    
    # Create temporary audio file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_audio:
        temp_audio_path = tmp_audio.name
    
    try:
        success = text_to_speech(
            text,
            language=language_code,
            voice_name=voice_name,
            save_file=temp_audio_path
        )
        
        if success and os.path.exists(temp_audio_path):
            with open(temp_audio_path, "rb") as audio_file:
                audio_bytes = audio_file.read()
            audio_base64 = base64.b64encode(audio_bytes).decode()
            return audio_base64
        
    except Exception as e:
        print(f"Audio generation failed: {e}")
        return None
    
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
        except:
            pass
    
    return None

def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="Traffic Safety Analyzer",
        page_icon="🚗",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    load_css()
    
    # Initialize session state for current audio tracking
    if 'current_audio_id' not in st.session_state:
        st.session_state.current_audio_id = None
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🚗 Traffic Safety Analyzer</h1>
        <p>Click an image or upload one to get AI safety reminders with voice</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # CSV file input
        csv_file = st.text_input(
            "📊 CSV Statistics File",
            value=DEFAULT_CSV,
            help="Path to the aggregation CSV file"
        )
        
        # Language selection
        language_choice = st.selectbox(
            "🌍 Language",
            options=["English", "Chinese", "Korean", "Japanese"],
            index=0,
            help="Select language for AI response and TTS"
        )
        
        # Voice selection
        voice_options = VOICE_OPTIONS[language_choice]
        
        selected_voice = st.selectbox(
            "🎤 Voice",
            options=list(voice_options.keys()),
            format_func=lambda x: voice_options[x],
            help="Select voice for text-to-speech"
        )
        
        # Azure services status
        st.subheader("🔑 Azure Services Status")
        openai_status = "✅ Connected" if os.getenv('AZURE_OPENAI_API_KEY') else "❌ Not configured"
        speech_status = "✅ Connected" if os.getenv('AZURE_SPEECH_KEY') else "❌ Not configured"
        st.write(f"**Azure OpenAI:** {openai_status}")
        st.write(f"**Azure Speech:** {speech_status}")
    
    # Main content - full width for images
    st.subheader("📸 Test Images")
    
    # Get available images
    available_images = get_available_images()
    
    if not available_images:
        st.warning(f"No test images found in {IMAGES_DIR}. Please run the data selector first.")
        return
    
    # Create larger image grid with fewer columns
    cols_per_row = 4
    for i in range(0, len(available_images), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j in range(cols_per_row):
            if i + j < len(available_images):
                img_info = available_images[i + j]
                
                with cols[j]:
                    # Display image first
                    st.image(
                        img_info['path'],
                        caption=f"{img_info['filename'][:20]}...",
                        use_container_width=True
                    )
                    
                    # Create clickable button below image
                    if st.button(
                        label="🔍 Analyze",
                        key=f"img_btn_{img_info['filename']}", 
                        help=f"Click to analyze {img_info['filename']}",
                        use_container_width=True,
                        type="secondary"
                    ):
                        # Stop existing audio but don't clear cache yet
                        stop_all_audio()
                        
                        # Set new image selection
                        st.session_state.selected_image = img_info
                        st.session_state.current_audio_id = f"audio_{int(time.time() * 1000)}"
                        
                        # Force rerun to ensure clean state
                        st.rerun()
    
    # Show modal for selected image
    if 'selected_image' in st.session_state:
        img_info = st.session_state.selected_image
        
        # Generate unique cache key for this image + settings combination
        cache_key = f"analysis_{img_info['filename']}_{language_choice}_{selected_voice}"
        
        # Generate analysis and audio only if not cached
        if cache_key not in st.session_state:
            with st.spinner("🤖 Analyzing traffic conditions..."):
                # Load and process label data
                label_data = load_label_data(img_info['label_path'])
                
                if label_data:
                    # Generate AI analysis
                    ai_reminder = analyze_with_ai_multilingual(label_data, csv_file, language_choice)
                    
                    # Generate audio
                    audio_base64 = None
                    if ai_reminder:
                        language_code = LANGUAGE_CODES[language_choice]
                        audio_base64 = generate_audio_base64(ai_reminder, language_code, selected_voice)
                    
                    # Cache the results
                    st.session_state[cache_key] = {
                        'ai_reminder': ai_reminder,
                        'audio_base64': audio_base64,
                        'label_data': label_data,
                        'timestamp': time.time()
                    }
        
        # Get cached analysis
        analysis_data = st.session_state.get(cache_key, {})
        
        # Create modal dialog
        @st.dialog(f"🔍 Analyzing: {img_info['filename']}")
        def show_analysis_modal():
            # Display enlarged image
            st.image(
                img_info['path'], 
                caption=f"Selected: {img_info['filename']}",
                use_container_width=True
            )
            
            # Display analysis if available
            if analysis_data:
                ai_reminder = analysis_data.get('ai_reminder')
                audio_base64 = analysis_data.get('audio_base64')
                label_data = analysis_data.get('label_data', {})
                
                if ai_reminder:
                    # Display AI reminder
                    st.markdown(f"""
                    <div class="safety-reminder">
                        <h4>⚠️ AI Safety Reminder</h4>
                        <p style="font-size: 1.1em;"><strong>{ai_reminder}</strong></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Display audio player if available
                    if audio_base64:
                        st.subheader("🎵 Audio Safety Reminder")
                        
                        # Use Streamlit's native audio component
                        try:
                            # Convert base64 to bytes for st.audio
                            audio_bytes = base64.b64decode(audio_base64)
                            st.audio(audio_bytes, format='audio/wav', autoplay=True)
                        except Exception as e:
                            st.error(f"Audio playback error: {e}")
                            
                            # Fallback to HTML audio if st.audio fails
                            unique_id = st.session_state.current_audio_id or f"audio_{int(time.time() * 1000)}"
                            audio_html = f"""
                            <audio id="{unique_id}" controls autoplay>
                                <source src="data:audio/wav;base64,{audio_base64}" type="audio/wav">
                                Your browser does not support the audio element.
                            </audio>
                            """
                            st.markdown(audio_html, unsafe_allow_html=True)
                    
                    # Show additional image metadata
                    with st.expander("📊 Image Details", expanded=True):
                        if 'attributes' in label_data:
                            attrs = label_data['attributes']
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Weather", attrs.get('weather', 'N/A'))
                                st.metric("Time", attrs.get('timeofday', 'N/A'))
                            with col_b:
                                st.metric("Scene", attrs.get('scene', 'N/A'))
                        
                        if 'labels' in label_data:
                            objects = [label.get('category', 'unknown') for label in label_data['labels']]
                            object_counts = {}
                            for obj in objects:
                                object_counts[obj] = object_counts.get(obj, 0) + 1
                            
                            st.write("**Detected Objects:**")
                            for obj, count in sorted(object_counts.items()):
                                st.write(f"• **{obj.title()}**: {count}")
            
            # Close button
            if st.button("✖️ Close", type="secondary", use_container_width=True):
                # Clear selected image but keep cache
                if 'selected_image' in st.session_state:
                    del st.session_state['selected_image']
                if 'current_audio_id' in st.session_state:
                    del st.session_state['current_audio_id']
                
                st.rerun()
        
        # Show the modal
        show_analysis_modal()

if __name__ == "__main__":
    main()