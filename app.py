# ------------------- Imports -------------------
import os
import re
import jwt
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS

# Pulling in your custom modules
from db import create_db_connection
from sentiment_engine import analyze_sentiment, generate_category_scores

# ------------------- Flask App -------------------
app = Flask(__name__)
CORS(app)

# Cloud Security Upgrade
SECRET_KEY = os.environ.get("SECRET_KEY", "Leilas_Super_Secret_Park_Ranger_Key_99!")

# ------------------- INPUT SANITIZATION -------------------
def sanitize_input(text):
    if not text:
        return ""
    return re.sub(r'<[^>]*?>', '', str(text))

# ------------------- JWT Decorator --------------------
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-token')

        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = data['username']
        except:
            return jsonify({"message": "Token is invalid!"}), 401

        return f(current_user, *args, **kwargs)
    return decorated

# ------------------- Home -------------------
@app.route("/")
def home():
    return "Park Ranger API Running ~ Phase 3 🚀"

# ------------------- LOGIN -------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = sanitize_input(data.get("username"))
    password = sanitize_input(data.get("password"))

    conn = create_db_connection()
    if not conn:
        return jsonify({"status": "db connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    # Fixed table name to lowercase 'user' and 'password_hash'
    cursor.execute(
        "SELECT * FROM user WHERE username=%s AND password_hash=%s",
        (username, password)
    )
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        token = jwt.encode({"username": username}, SECRET_KEY, algorithm="HS256")
        return jsonify({"status": "success", "token": token})

    return jsonify({"status": "failed"}), 401

# ------------------- PRODUCTS -------------------
@app.route("/products", methods=["POST"])
@token_required
def add_product(current_user):
    data = request.json

    name = sanitize_input(data.get("product_name"))
    tier = sanitize_input(data.get("performance_tier", ""))
    rate = float(data.get("sentiment_rate", 0))

    conn = create_db_connection()
    if not conn:
        return jsonify({"status": "db connection failed"}), 500

    cursor = conn.cursor()
    # Fixed table name to lowercase 'product'
    cursor.execute(
        "INSERT INTO product (product_name, performance_tier, sentiment_rate) VALUES (%s,%s,%s)",
        (name, tier, rate)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"status": "product added"})

@app.route("/products", methods=["GET"])
def get_products():
    conn = create_db_connection()
    if not conn:
        return jsonify({"status": "db connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    # Fixed table name to lowercase 'product'
    cursor.execute("SELECT * FROM product")
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(products)

# ------------------- FEEDBACK (WITH NLP) -------------------
@app.route("/feedback", methods=["POST"])
@token_required
def add_feedback(current_user):
    data = request.json

    try:
        loc_id = int(data.get("location_id"))
        prod_id = int(data.get("product_id"))
        src_id = int(data.get("source_id"))
        text = sanitize_input(data.get("feedback_text"))

        if not loc_id or not prod_id or not src_id or not text.strip():
            return jsonify({"status": "missing or invalid fields"}), 400

        # NLP
        label, score = analyze_sentiment(text)

        conn = create_db_connection()
        if not conn:
            return jsonify({"status": "db connection failed"}), 500

        cursor = conn.cursor()

        # Fixed table name to lowercase 'feedback'
        cursor.execute(
            """INSERT INTO feedback 
            (location_id, product_id, source_id, feedback_text, sentiment_label, sentiment_score) 
            VALUES (%s,%s,%s,%s,%s,%s)""",
            (loc_id, prod_id, src_id, text, label, score)
        )

        feedback_id = cursor.lastrowid

        # Generate category ratings
        scores = generate_category_scores(score)

        # Fixed table name to lowercase 'category_rating'
        cursor.execute(
            """INSERT INTO category_rating 
            (feedback_id, taste_score, quality_score, value_score, service_score, presentation_score)
            VALUES (%s,%s,%s,%s,%s,%s)""",
            (
                feedback_id,
                scores["taste_score"],
                scores["quality_score"],
                scores["value_score"],
                scores["service_score"],
                scores["presentation_score"]
            )
        )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "status": "feedback added",
            "sentiment_label": label,
            "sentiment_score": score,
            "category_scores": scores
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------- GET FEEDBACK WITH RATINGS -------------------
@app.route("/feedback", methods=["GET"])
def get_feedback():
    conn = create_db_connection()
    if not conn:
        return jsonify({"status": "db connection failed"}), 500

    cursor = conn.cursor(dictionary=True)

    # Fixed table names to lowercase 'feedback' and 'category_rating'
    cursor.execute("""
        SELECT f.*, c.taste_score, c.quality_score, c.value_score,
               c.service_score, c.presentation_score
        FROM feedback f
        LEFT JOIN category_rating c ON f.feedback_id = c.feedback_id
    """)

    feedbacks = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(feedbacks)

# ------------------- LOCATIONS -------------------
@app.route('/locations', methods=['GET'])
def get_locations():
    conn = create_db_connection()
    if not conn:
        return jsonify({"status": "db connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    # Fixed table name to lowercase 'location'
    cursor.execute("SELECT * FROM location")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(rows)

# ------------------- RUN -------------------
if __name__ == "__main__":
    app.run(debug=True)