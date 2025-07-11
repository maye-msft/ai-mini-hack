"""
 Traffic Safety Analyzer

"""

import json
import pandas as pd
from openai import AzureOpenAI
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file  
import os
import argparse
import sys
try:
    import azure.cognitiveservices.speech as speechsdk
    SPEECH_SDK_AVAILABLE = True
except ImportError:
    SPEECH_SDK_AVAILABLE = False
    print("Azure Speech SDK not available. TTS functionality will be disabled.")

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Pygame not available. Audio playback will be limited.")

import io
import tempfile

def analyze_traffic(json_data, csv_file='3_aggregation.csv'):
    """
    One function to analyze traffic and get safety reminder
    
    Args:
        json_data: Your image detection JSON data
        csv_file: Path to statistics CSV file
    
    Returns:
        dict: Analysis results including reminder and statistical context
    """
    
    # Extract info from JSON
    weather = json_data.get('metadata', {}).get('weather') or json_data.get('attributes', {}).get('weather')
    timeofday = json_data.get('metadata', {}).get('timeofday') or json_data.get('attributes', {}).get('timeofday')
    scene = json_data.get('metadata', {}).get('scene') or json_data.get('attributes', {}).get('scene')
    
    # Category mapping
    category_mapping = {
        'car': 'vehicle', 'truck': 'vehicle', 'bus': 'vehicle',
        'bicycle': 'vehicle', 'motorcycle': 'vehicle', 'other vehicle': 'vehicle',
        'train': 'vehicle', 'trailer': 'vehicle',
        'traffic sign': 'traffic_sign', 'traffic light': 'traffic_sign',
        'pedestrian': 'pedestrian', 'rider': 'pedestrian', 'other person': 'pedestrian'
    }
    
    # Count detected objects by category
    object_counts = {}
    for label in json_data.get('labels', []):
        category = label.get('category', '')
        mapped_category = category_mapping.get(category, category)
        object_counts[mapped_category] = object_counts.get(mapped_category, 0) + 1
    
    # Load statistics and analyze each category
    analysis_results = {}
    try:
        df = pd.read_csv(csv_file)
        
        for category, current_count in object_counts.items():
            # Find historical statistics for this category
            stats = df[
                (df['weather'] == weather) &
                (df['timeofday'] == timeofday) &
                (df['scene'] == scene) &
                (df['mapped_category'] == category)
            ]
            
            if len(stats) > 0:
                stat = stats.iloc[0]
                avg = stat['avg_count']
                q1, q3 = stat['q1_count'], stat['q3_count']
                min_count, max_count = stat['min_count'], stat['max_count']
                
                # Determine level based on quartiles
                if current_count < q1:
                    level = 'below_normal'
                    level_desc = f"below normal (Q1: {q1})"
                elif current_count > q3:
                    level = 'above_normal'
                    level_desc = f"above normal (Q3: {q3})"
                else:
                    level = 'normal'
                    level_desc = "within normal range"
                
                analysis_results[category] = {
                    'current_count': current_count,
                    'historical_avg': avg,
                    'level': level,
                    'level_description': level_desc,
                    'quartile_range': f"Q1: {q1}, Q3: {q3}",
                    'full_range': f"Min: {min_count}, Max: {max_count}",
                    'percentile_position': calculate_percentile(current_count, stat)
                }
    
    except Exception as e:
        print(f"Error loading statistics: {e}")
    
    # Generate reminder using  analysis
    reminder = generate_data_driven_reminder(weather, timeofday, scene, analysis_results)
    
    return {
        'environment': {'weather': weather, 'time': timeofday, 'scene': scene},
        'detections': object_counts,
        'statistical_analysis': analysis_results,
        'safety_reminder': reminder
    }

def calculate_percentile(current_count, stats):
    """Calculate approximate percentile position"""
    q1, median, q3 = stats['q1_count'], stats['median_count'], stats['q3_count']
    
    if current_count <= q1:
        return "bottom 25%"
    elif current_count <= median:
        return "25th-50th percentile"
    elif current_count <= q3:
        return "50th-75th percentile"
    else:
        return "top 25%"

def generate_data_driven_reminder(weather, timeofday, scene, analysis_results):
    """Generate reminder using actual statistical analysis"""
    
    # Weather takes priority regardless of traffic data
    weather_priority_reminders = {
        'rainy': "Rainy conditions - reduce speed, increase following distance, and use caution",
        'snowy': "Snow on roadway - drive slowly and carefully, allow extra stopping distance",
        'foggy': "Foggy conditions - use fog lights, reduce speed, and stay alert"
    }
    
    if weather in weather_priority_reminders:
        return weather_priority_reminders[weather]
    
    # Use statistical analysis for traffic-based decisions
    vehicle_analysis = analysis_results.get('vehicle', {})
    pedestrian_analysis = analysis_results.get('pedestrian', {})
    
    # Vehicle traffic analysis
    if vehicle_analysis:
        vehicle_level = vehicle_analysis.get('level')
        vehicle_count = vehicle_analysis.get('current_count', 0)
        vehicle_avg = vehicle_analysis.get('historical_avg', 0)
        
        if vehicle_level == 'above_normal':
            return f"Heavy traffic detected ({vehicle_count} vs avg {vehicle_avg:.1f}) - maintain safe following distance and stay patient"
        elif vehicle_level == 'below_normal' and scene == 'highway':
            return f"Light highway traffic ({vehicle_count} vs avg {vehicle_avg:.1f}) - maintain appropriate speeds and stay focused"
    
    # Pedestrian analysis based on data
    if pedestrian_analysis:
        ped_level = pedestrian_analysis.get('level')
        ped_count = pedestrian_analysis.get('current_count', 0)
        
        if ped_level == 'above_normal':
            return f"High pedestrian activity detected - reduce speed and watch for foot traffic"
    
    # Time-based reminders when no significant traffic anomalies
    if timeofday == 'night':
        return "Night driving - use headlights and exercise extra caution"
    elif timeofday == 'dawn/dusk':
        return "Low light conditions - turn on headlights and drive carefully"
    
    # Default for normal statistical conditions
    return "Normal driving conditions based on historical data - maintain safe speeds and stay alert"

def analyze_with_ai(json_data, csv_file='3_aggregation.csv'):
    """
    Enhanced version using Azure OpenAI with statistical context
    """
    
    if not os.getenv('AZURE_OPENAI_API_KEY'):
        result = analyze_traffic(json_data, csv_file)
        return result['safety_reminder']
    
    try:
        # Get comprehensive analysis with statistical context
        analysis = analyze_traffic(json_data, csv_file)
        
        # Build statistical context for AI prompt
        statistical_context = []
        for category, data in analysis['statistical_analysis'].items():
            context_line = (f"{category}: {data['current_count']} detected "
                          f"(historical avg: {data['historical_avg']:.1f}, "
                          f"level: {data['level_description']}, "
                          f"percentile: {data['percentile_position']})")
            statistical_context.append(context_line)
        
        env = analysis['environment']
        
        # Create data-rich prompt for AI
        client = AzureOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version='2024-12-01-preview'
        )
        
        prompt = f"""
Generate a precise traffic safety reminder (25-40 words) based on this  analysis:

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
- Response in English
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
        result = analyze_traffic(json_data, csv_file)
        return result['safety_reminder']

def text_to_speech(text, language="en-US", voice_name=None, save_file=None):
    """
    Convert text to speech using Azure Speech Services
    
    Args:
        text: Text to convert to speech
        language: Language code (default: en-US for English)
        voice_name: Optional custom voice name override
        save_file: Optional path to save audio file (e.g., 'output.wav')
    """
    if not SPEECH_SDK_AVAILABLE:
        print("Azure Speech SDK not available. Skipping TTS.")
        return False
        
    try:
        # Configure speech service
        speech_key = os.getenv('AZURE_SPEECH_KEY')
        speech_region = os.getenv('AZURE_SPEECH_REGION')
        
        if not speech_key or not speech_region:
            print("Azure Speech credentials not found. Skipping TTS.")
            return False
            
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
        
        # Set voice based on language or custom voice
        if voice_name:
            speech_config.speech_synthesis_voice_name = voice_name
        elif language == "zh-CN":
            speech_config.speech_synthesis_voice_name = "zh-CN-XiaoxiaoNeural"
        elif language == "en-US":
            speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
        else:
            speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
            
        # Configure audio output
        if save_file:
            audio_config = speechsdk.audio.AudioOutputConfig(filename=save_file)
        else:
            audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        
        # Create synthesizer
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        
        # Synthesize speech
        if save_file:
            print(f"🔊 Saving audio to: {save_file}")
            print(f"📝 Text: {text}")
        else:
            print(f"🔊 Playing audio: {text}")
        
        result = synthesizer.speak_text_async(text).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            if save_file:
                print(f"✅ Audio saved to {save_file}")
            else:
                print("✅ Audio playback completed")
            return True
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print(f"❌ Speech synthesis canceled: {cancellation_details.reason}")
            if cancellation_details.error_details:
                print(f"Error details: {cancellation_details.error_details}")
            return False
            
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        return False

def play_audio_file(file_path):
    """
    Play audio file using multiple fallback methods
    
    Args:
        file_path: Path to the audio file to play
    """
    # Method 1: Try system commands first
    try:
        import subprocess
        # Try different system audio players
        audio_players = ['aplay', 'paplay', 'afplay', 'mpg123', 'ffplay']
        
        for player in audio_players:
            try:
                result = subprocess.run([player, file_path], 
                                      capture_output=True, 
                                      timeout=30,
                                      check=True)
                print(f"✅ Audio played successfully with {player}")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
                
    except Exception:
        pass
    
    # Method 2: Try pygame as fallback
    if PYGAME_AVAILABLE:
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            print(f"🔊 Playing audio file with pygame: {file_path}")
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
                
            print("✅ Audio playback completed")
            pygame.mixer.quit()
            return True
            
        except Exception as e:
            print(f"❌ Pygame audio error: {e}")
    
    # Method 3: Web browser fallback
    try:
        import webbrowser
        import urllib.parse
        file_url = f"file://{os.path.abspath(file_path)}"
        print(f"🌐 Opening audio in browser: {file_path}")
        webbrowser.open(file_url)
        return True
    except Exception as e:
        print(f"❌ Browser audio error: {e}")
    
    print("❌ All audio playback methods failed")
    return False

# ============ USAGE EXAMPLES ============

def main():
    """Main function with CLI argument parsing"""
    parser = argparse.ArgumentParser(description='Traffic Safety Analyzer')
    parser.add_argument('--json', '-j', required=True, help='Path to JSON file with detection data')
    parser.add_argument('--csv', '-c', default='3_aggregation.csv', help='Path to CSV file with statistics (default: 3_aggregation.csv)')
    parser.add_argument('--ai', action='store_true', help='Use AI analysis with Azure OpenAI')
    parser.add_argument('--tts', action='store_true', help='Enable text-to-speech for AI responses')
    parser.add_argument('--lang', default='en-US', help='Language for TTS (default: en-US)')
    
    args = parser.parse_args()
    
    # Load JSON data
    try:
        with open(args.json, 'r') as f:
            json_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file '{args.json}' not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{args.json}'")
        sys.exit(1)
    
    # Check if CSV file exists
    if not os.path.exists(args.csv):
        print(f"Warning: CSV file '{args.csv}' not found. Analysis will proceed without statistical context.")
    
    print("Traffic Safety Analysis with Statistical Context")
    print("=" * 50)
    
    if args.ai:
        # AI analysis
        print("🤖 AI Analysis with Statistical Context:")
        ai_reminder = analyze_with_ai(json_data, args.csv)
        print(f"   {ai_reminder}")
        
        # Play TTS if enabled
        if args.tts and ai_reminder:
            # Save audio file and try to play it
            audio_file = "safety_reminder.wav"
            success = text_to_speech(ai_reminder, args.lang, save_file=audio_file)
            if success:
                print(f"🎵 Audio file created: {audio_file}")
                # Try to play the audio file
                play_success = play_audio_file(audio_file)
                if not play_success:
                    print("   You can download and play this file to hear the safety reminder.")
    else:
        # Comprehensive analysis
        result = analyze_traffic(json_data, args.csv)
        
        env = result['environment']
        print(f"📍 Environment: {env['weather']} | {env['time']} | {env['scene']}")
        
        print(f"🚗 Detections: ", end="")
        detections = [f"{k}: {v}" for k, v in result['detections'].items()]
        print(", ".join(detections))
        
        print(f"\n📊 Statistical Analysis:")
        for category, analysis in result['statistical_analysis'].items():
            print(f"   {category}: {analysis['current_count']} detected")
            print(f"      Historical average: {analysis['historical_avg']:.1f}")
            print(f"      Level: {analysis['level_description']}")
            print(f"      Position: {analysis['percentile_position']}")
            print(f"      Range: {analysis['quartile_range']}")
        
        print(f"\n⚠️   Reminder: {result['safety_reminder']}")


if __name__ == "__main__":
    main()

