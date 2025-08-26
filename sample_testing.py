from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import re
import logging
from datetime import datetime
import time
from googletrans import Translator

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Precompile regex patterns
QUESTION_PATTERN = re.compile(r"^(.+?)\s*=>\s*(.+)$", re.IGNORECASE)
COMMENT_PATTERN = re.compile(r"^\s*#")

translator = Translator()

class ChatBotEngine:
    def __init__(self, data_path="campus.txt"):
        self.responses = self._load_responses(data_path)
        self.default_responses = [
            "I'm sorry, could you rephrase that question?",
            "I don't have that information right now. Maybe try asking something else?",
            "Could you provide more details about your query?",
        ]
        logger.info(f"Loaded {len(self.responses)} response patterns")

    def _load_responses(self, file_path):
        responses = {}
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                current_section = "General"
                for line_number, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or COMMENT_PATTERN.match(line):
                        continue
                    if line.startswith("#"):
                        current_section = line[1:].strip()
                        continue

                    match = QUESTION_PATTERN.match(line)
                    if match:
                        pattern, response = match.groups()
                        try:
                            compiled_pattern = re.compile(pattern, re.IGNORECASE)
                            responses[compiled_pattern] = {
                                "response": response,
                                "section": current_section,
                                "pattern": pattern
                            }
                        except re.error as e:
                            logger.error(f"Regex error in line {line_number}: {e}")
                    else:
                        logger.warning(f"Invalid format in line {line_number}: {line}")
        except FileNotFoundError:
            logger.error(f"Data file not found: {file_path}")
        except Exception as e:
            logger.error(f"Error loading responses: {str(e)}")
        return responses

    def get_response(self, user_input, target_lang="en"):
        start_time = time.time()
        user_input = user_input.strip()

        # Translate to English
        try:
            translated_input = translator.translate(user_input, dest='en').text.lower()
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return "Translation failed. Please try again."

        # Search for matching patterns
        for pattern, data in self.responses.items():
            if pattern.search(translated_input):
                response_en = data["response"]
                try:
                    return translator.translate(response_en, dest=target_lang).text
                except Exception as e:
                    logger.error(f"Translation error: {e}")
                    return response_en

        fallback_response = self.default_responses[len(user_input) % len(self.default_responses)]
        try:
            return translator.translate(fallback_response, dest=target_lang).text
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return fallback_response

chat_engine = ChatBotEngine()

@app.route("/")
def home():
    return render_template("index19.html")

@app.route("/get", methods=["POST"])
def handle_chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        user_lang = data.get("lang", "en")

        if not user_message:
            return jsonify({"error": "Empty message received"}), 400

        response = chat_engine.get_response(user_message, target_lang=user_lang)
        logger.info(f"Request: {user_message} | Language: {user_lang} | Response: {response}")

        return jsonify({
            "response": response,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)