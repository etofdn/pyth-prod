#!/usr/bin/env python3
"""
transcript_analyzer.py

Analyzes the transcript data to find:
1) Most frequently used words
2) Most repeated text chunks
3) Word frequency distribution
4) Speaker analysis

Usage:
    python transcript_analyzer.py
"""

import json
import re
from collections import Counter, defaultdict
from typing import List, Dict, Tuple

class TranscriptAnalyzer:
    def __init__(self, transcript_file: str = "flattened_transcript.json"):
        self.transcript_file = transcript_file
        self.data = self.load_data()
        
    def load_data(self) -> List[Dict]:
        """Load transcript data from JSON file"""
        try:
            with open(self.transcript_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"Loaded {len(data)} documents from {self.transcript_file}")
            return data
        except Exception as e:
            print(f"Error loading data: {e}")
            return []
    
    def extract_text_chunks(self) -> List[str]:
        """Extract all text chunks from the transcript"""
        chunks = []
        for item in self.data:
            if item.get("text"):
                chunks.append(item["text"].strip())
        return chunks
    
    def clean_text(self, text: str) -> str:
        """Clean text for word analysis"""
        # Remove punctuation and convert to lowercase
        text = re.sub(r'[^\w\s]', '', text.lower())
        return text
    
    def get_word_frequency(self, min_length: int = 3) -> Counter:
        """Get word frequency analysis"""
        word_counter = Counter()
        
        for chunk in self.extract_text_chunks():
            cleaned_text = self.clean_text(chunk)
            words = cleaned_text.split()
            # Filter out short words and common stop words
            stop_words = {'the', 'and', 'that', 'this', 'with', 'for', 'are', 'but', 'they', 'have', 'had', 'what', 'said', 'each', 'which', 'she', 'do', 'how', 'their', 'if', 'will', 'up', 'other', 'about', 'out', 'many', 'then', 'them', 'these', 'so', 'some', 'her', 'would', 'make', 'like', 'into', 'him', 'time', 'two', 'more', 'go', 'no', 'way', 'could', 'my', 'than', 'first', 'been', 'call', 'who', 'its', 'now', 'find', 'long', 'down', 'day', 'did', 'get', 'come', 'made', 'may', 'part'}
            
            for word in words:
                if len(word) >= min_length and word not in stop_words:
                    word_counter[word] += 1
        
        return word_counter
    
    def get_chunk_frequency(self, min_length: int = 10) -> Counter:
        """Get frequency of repeated text chunks"""
        chunk_counter = Counter()
        
        for chunk in self.extract_text_chunks():
            if len(chunk) >= min_length:
                chunk_counter[chunk] += 1
        
        return chunk_counter
    
    def get_speaker_analysis(self) -> Dict:
        """Analyze text by speaker"""
        speaker_texts = defaultdict(list)
        
        for item in self.data:
            if item.get("text") and item.get("speaker") is not None:
                speaker_texts[item["speaker"]].append(item["text"])
        
        speaker_stats = {}
        for speaker, texts in speaker_texts.items():
            total_words = sum(len(text.split()) for text in texts)
            total_chunks = len(texts)
            avg_chunk_length = total_words / total_chunks if total_chunks > 0 else 0
            
            speaker_stats[speaker] = {
                "total_chunks": total_chunks,
                "total_words": total_words,
                "avg_chunk_length": round(avg_chunk_length, 2),
                "total_text": " ".join(texts)
            }
        
        return speaker_stats
    
    def analyze_most_common_words(self, top_n: int = 20):
        """Analyze and display most common words"""
        print("\n" + "="*50)
        print("MOST COMMON WORDS ANALYSIS")
        print("="*50)
        
        word_freq = self.get_word_frequency()
        
        if not word_freq:
            print("No words found in transcript.")
            return
        
        print(f"\nTop {top_n} most frequent words:")
        print("-" * 40)
        for i, (word, count) in enumerate(word_freq.most_common(top_n), 1):
            print(f"{i:2d}. {word:15s} - {count:3d} occurrences")
        
        # Show some statistics
        total_words = sum(word_freq.values())
        unique_words = len(word_freq)
        print(f"\nStatistics:")
        print(f"  Total word occurrences: {total_words}")
        print(f"  Unique words: {unique_words}")
        print(f"  Average frequency: {total_words/unique_words:.2f}")
    
    def analyze_repeated_chunks(self, top_n: int = 10):
        """Analyze and display most repeated text chunks"""
        print("\n" + "="*50)
        print("MOST REPEATED TEXT CHUNKS")
        print("="*50)
        
        chunk_freq = self.get_chunk_frequency()
        
        if not chunk_freq:
            print("No repeated chunks found.")
            return
        
        # Filter chunks that appear more than once
        repeated_chunks = {chunk: count for chunk, count in chunk_freq.items() if count > 1}
        
        if not repeated_chunks:
            print("No repeated chunks found.")
            return
        
        print(f"\nTop {top_n} most repeated chunks:")
        print("-" * 60)
        for i, (chunk, count) in enumerate(sorted(repeated_chunks.items(), key=lambda x: x[1], reverse=True)[:top_n], 1):
            # Truncate long chunks for display
            display_chunk = chunk[:80] + "..." if len(chunk) > 80 else chunk
            print(f"{i:2d}. [{count} times] {display_chunk}")
        
        print(f"\nTotal repeated chunks: {len(repeated_chunks)}")
    
    def analyze_speakers(self):
        """Analyze text distribution by speaker"""
        print("\n" + "="*50)
        print("SPEAKER ANALYSIS")
        print("="*50)
        
        speaker_stats = self.get_speaker_analysis()
        
        if not speaker_stats:
            print("No speaker data found.")
            return
        
        print(f"\nSpeaker statistics:")
        print("-" * 50)
        for speaker, stats in speaker_stats.items():
            print(f"Speaker {speaker}:")
            print(f"  Total chunks: {stats['total_chunks']}")
            print(f"  Total words: {stats['total_words']}")
            print(f"  Avg chunk length: {stats['avg_chunk_length']} words")
            print()
    
    def run_full_analysis(self):
        """Run complete analysis"""
        print("TRANSCRIPT ANALYSIS")
        print("="*50)
        print(f"Analyzing: {self.transcript_file}")
        
        if not self.data:
            print("No data to analyze.")
            return
        
        # Run all analyses
        self.analyze_most_common_words()
        self.analyze_repeated_chunks()
        self.analyze_speakers()
        
        print("\n" + "="*50)
        print("ANALYSIS COMPLETE")
        print("="*50)

def main():
    analyzer = TranscriptAnalyzer()
    
    print("Choose analysis type:")
    print("  1) Most common words")
    print("  2) Most repeated chunks")
    print("  3) Speaker analysis")
    print("  4) Full analysis")
    
    choice = input("\nEnter 1-4: ").strip()
    
    if choice == "1":
        analyzer.analyze_most_common_words()
    elif choice == "2":
        analyzer.analyze_repeated_chunks()
    elif choice == "3":
        analyzer.analyze_speakers()
    elif choice == "4":
        analyzer.run_full_analysis()
    else:
        print("Invalid choice. Running full analysis...")
        analyzer.run_full_analysis()

if __name__ == "__main__":
    main() 