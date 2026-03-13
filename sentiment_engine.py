from textblob import TextBlob
import random

# ------------------- SENTIMENT ANALYSIS -------------------

def analyze_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # -1 to 1

    # Labeling
    if polarity > 0.1:
        label = "Positive"
    elif polarity < -0.1:
        label = "Negative"
    else:
        label = "Neutral"

    return label, polarity


# ------------------- CATEGORY SCORE GENERATOR -------------------
def generate_category_scores(sentiment_score):
    """
    Convert sentiment score into category ratings (1–5)
    """

    # Normalize score (-1 to 1) → (1 to 5)
    base_score = int(((sentiment_score + 1) / 2) * 4) + 1

    def clamp(val):
        return max(1, min(5, val))

    return {
        "taste_score": clamp(base_score + random.randint(-1, 1)),
        "quality_score": clamp(base_score + random.randint(-1, 1)),
        "value_score": clamp(base_score + random.randint(-1, 1)),
        "service_score": clamp(base_score + random.randint(-1, 1)),
        "presentation_score": clamp(base_score + random.randint(-1, 1)),
    }
