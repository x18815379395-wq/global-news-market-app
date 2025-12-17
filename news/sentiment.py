"""
Sentiment analysis functionality for news items.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from news.models import NewsItem

logger = logging.getLogger(__name__)

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    logger.warning("VADER sentiment analyzer not available. Sentiment analysis will be disabled.")
    VADER_AVAILABLE = False


def _get_sentiment_label(score: float) -> str:
    """Map sentiment score to label.
    
    Args:
        score: Sentiment score between -1 (negative) and 1 (positive).
        
    Returns:
        Sentiment label ("positive", "negative", or "neutral").
    """
    if score > 0.05:
        return "positive"
    elif score < -0.05:
        return "negative"
    else:
        return "neutral"


class SentimentAnalyzer:
    """
    Analyzes sentiment of news items using VADER sentiment analyzer.
    """
    
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer() if VADER_AVAILABLE else None
        self.enabled = VADER_AVAILABLE
    
    def analyze(self, item: NewsItem) -> NewsItem:
        """
        Analyze sentiment of a single news item.
        
        Args:
            item: NewsItem to analyze.
            
        Returns:
            NewsItem with sentiment analysis results added.
        """
        if not self.enabled:
            return item
        
        try:
            # Combine title and description for better sentiment analysis
            text = f"{item.title} {item.description}"
            
            # Analyze sentiment
            sentiment = self.analyzer.polarity_scores(text)
            
            # Extract sentiment score and label
            compound_score = sentiment["compound"]
            label = _get_sentiment_label(compound_score)
            
            # Update news item with sentiment analysis results
            item.sentiment_score = compound_score
            item.sentiment_label = label
            item.sentiment_dimensions = {
                "negative": sentiment["neg"],
                "neutral": sentiment["neu"],
                "positive": sentiment["pos"],
            }
            
        except Exception as exc:
            logger.error(f"Sentiment analysis failed for news item {item.url}: {exc}")
        
        return item
    
    def analyze_batch(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        Analyze sentiment of multiple news items in batch.
        
        Args:
            items: List of NewsItems to analyze.
            
        Returns:
            List of NewsItems with sentiment analysis results added.
        """
        if not self.enabled:
            return items
        
        return [self.analyze(item) for item in items]
    
    def get_sentiment_trend(self, items: List[NewsItem], window_hours: int = 24) -> Dict[str, float]:
        """
        Get sentiment trend for news items within a specified time window.
        
        Args:
            items: List of NewsItems to analyze.
            window_hours: Time window in hours.
            
        Returns:
            Dict with sentiment trend metrics.
        """
        if not items:
            return {
                "average_sentiment": 0.0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "total_count": 0,
            }
        
        # Filter items within time window
        now = datetime.now()
        window_start = now - timedelta(hours=window_hours)
        
        recent_items = []
        for item in items:
            if item.published_at and item.published_at >= window_start:
                recent_items.append(item)
        
        if not recent_items:
            return {
                "average_sentiment": 0.0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "total_count": 0,
            }
        
        # Calculate sentiment metrics
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        total_sentiment = 0.0
        
        for item in recent_items:
            if item.sentiment_score is not None:
                total_sentiment += item.sentiment_score
            
            if item.sentiment_label == "positive":
                positive_count += 1
            elif item.sentiment_label == "negative":
                negative_count += 1
            else:
                neutral_count += 1
        
        return {
            "average_sentiment": total_sentiment / len(recent_items),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "total_count": len(recent_items),
        }
