
import asyncio
import os
import websockets
import google.generativeai as genai
from gtts import gTTS
import io
import wave

# Fetch Environment Variables from Render Config
API_KEY = os.environ.get("GEMINI_API_KEY")
PORT = int(os.environ.get("PORT", 8765))

if not API_KEY:
    print("WARNING: GEMINI_API_KEY environment variable is not set!")

# Initialize Gemini Client
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

async def handle_bot_logic(websocket):
    print(f"ESP32 Connected from: {websocket.remote_address}")
    
    try:
        async for message in websocket:
            if isinstance(message, bytes):
                print("Received raw analog audio bytes from ESP32...")
                
                # Convert the raw 8-bit data into a valid WAV file structure in memory
                wav_io = io.BytesIO()
                with wave.open(wav_io, 'wb') as wav_file:
                    wav_file.setnchannels(1)       # Mono Audio
                    wav_file.setsampwidth(1)      # 1 byte = 8-bit audio sample depth
                    wav_file.setframerate(8000)   # 8kHz sample rate matches ESP32 sketch
                    wav_file.writeframes(message)
                
                wav_io.seek(0)
                wav_bytes = wav_io.read()

                # Package the audio bytes for Gemini API
                audio_data = {
                    "data": wav_bytes,
                    "mime_type": "audio/wav"
                }
                
                print("Sending voice query to Gemini...")
                response = model.generate_content([
                    audio_data, 
                    "You are a standalone voice assistant gadget. Provide a very brief, friendly, conversational reply under 2 sentences."
                ])
                
                bot_text_reply = response.text
                print(f"Gemini Reply: {bot_text_reply}")
                
                # Convert text answer to voice bytes using Google TTS
                print("Generating voice reply...")
                tts = gTTS(text=bot_text_reply, lang='en', slow=False)
                mp3_fp = io.BytesIO()
                tts.write_to_fp(mp3_fp)
                mp3_fp.seek(0)
                
                # Stream the compiled audio bytes back to the ESP32 speaker
                print("Streaming audio response to ESP32...")
                await websocket.send(mp3_fp.read())
                
    except websockets.exceptions.ConnectionClosed:
        print("ESP32 Client disconnected.")
    except Exception as e:
        print(f"An error occurred: {e}")

async def main():
    # Bind to 0.0.0.0 to allow external connections from your ESP32
    async with websockets.serve(handle_bot_logic, "0.0.0.0", PORT):
        print(f"Cloud Python Server actively running on port {PORT}...")
        await asyncio.Future() # Keeps server alive indefinitely

if __name__ == "__main__":
    asyncio.run(main())

