# Open Source ML Algorithms for Podcast UX Enhancement

This document outlines open-source Python ML tools that can enhance the viewer/listener experience for the Murder Index podcast.

---

## 1. **Content-Based Case Recommendation** 
**Goal:** Recommend similar unsolved cases based on listener interests.

### Tools:
- **scikit-learn** - TF-IDF + Cosine Similarity
  ```python
  from sklearn.feature_extraction.text import TfidfVectorizer
  from sklearn.metrics.pairwise import cosine_similarity
  
  # Vectorize case summaries
  vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
  tfidf_matrix = vectorizer.fit_transform(case_summaries)
  
  # Find similar cases
  similarities = cosine_similarity(tfidf_matrix[case_idx], tfidf_matrix)
  ```

- **sentence-transformers** - Semantic similarity with embeddings
  ```python
  from sentence_transformers import SentenceTransformer
  
  model = SentenceTransformer('all-MiniLM-L6-v2')
  embeddings = model.encode(case_summaries)
  ```

**Use Case:** "Listeners who found the Minneapolis case interesting might also like these 5 similar unsolved cases..."

---

## 2. **Audio Transcription & Speaker Diarization**
**Goal:** Auto-generate transcripts with speaker labels (Maya vs Dr. Thorne).

### Tools:
- **OpenAI Whisper** (open source) - Best-in-class transcription
  ```python
  import whisper
  
  model = whisper.load_model("base")  # or "small", "medium", "large"
  result = model.transcribe("episode.mp3")
  ```

- **pyannote-audio** - Speaker diarization
  ```python
  from pyannote.audio import Pipeline
  
  pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")
  diarization = pipeline("episode.mp3")
  
  for turn, _, speaker in diarization.itertracks(yield_label=True):
      print(f"{turn.start:.1f}s - {turn.end:.1f}s: {speaker}")
  ```

**Use Case:** Auto-sync visual cues with dialogue, generate searchable transcripts.

---

## 3. **Named Entity Recognition (NER) for Case Facts**
**Goal:** Extract key entities from case descriptions (names, locations, dates, evidence).

### Tools:
- **spaCy** - Fast NER with pre-trained models
  ```python
  import spacy
  
  nlp = spacy.load("en_core_web_lg")
  doc = nlp(case_summary)
  
  for ent in doc.ents:
      print(f"{ent.text} -> {ent.label_}")
      # "Minneapolis" -> GPE, "December 14, 1987" -> DATE
  ```

- **Flair** - State-of-the-art NER
  ```python
  from flair.data import Sentence
  from flair.models import SequenceTagger
  
  tagger = SequenceTagger.load("flair/ner-english-large")
  sentence = Sentence(case_text)
  tagger.predict(sentence)
  ```

**Use Case:** Auto-tag cases, build knowledge graphs, enable faceted search.

---

## 4. **Sentiment & Tone Analysis**
**Goal:** Detect emotional moments in narration for visual cue timing.

### Tools:
- **transformers (Hugging Face)** - Pre-trained sentiment models
  ```python
  from transformers import pipeline
  
  classifier = pipeline("sentiment-analysis", 
                        model="cardiffnlp/twitter-roberta-base-sentiment")
  result = classifier("The body was found in a shallow grave...")
  ```

- **TextBlob** - Simple polarity/subjectivity
  ```python
  from textblob import TextBlob
  
  blob = TextBlob(text)
  print(f"Polarity: {blob.sentiment.polarity}")  # -1 to 1
  ```

**Use Case:** Darken visuals during tense moments, highlight dramatic reveals.

---

## 5. **Topic Modeling for Case Clustering**
**Goal:** Group cases by theme (domestic violence, gang-related, random, etc.).

### Tools:
- **BERTopic** - Modern topic modeling
  ```python
  from bertopic import BERTopic
  
  topic_model = BERTopic()
  topics, probs = topic_model.fit_transform(case_summaries)
  topic_model.visualize_topics()
  ```

- **Gensim LDA** - Classic approach
  ```python
  from gensim import corpora
  from gensim.models import LdaModel
  
  dictionary = corpora.Dictionary(tokenized_docs)
  corpus = [dictionary.doc2bow(doc) for doc in tokenized_docs]
  lda = LdaModel(corpus, num_topics=10, id2word=dictionary)
  ```

**Use Case:** "Browse cases by theme: Serial Cases | Cold Trail | Domestic | Unknown"

---

## 6. **Geographic Clustering & Heatmaps**
**Goal:** Visualize case distribution, find hotspots.

### Tools:
- **scikit-learn DBSCAN** - Density-based clustering
  ```python
  from sklearn.cluster import DBSCAN
  import numpy as np
  
  coords = np.array([[lat, lon] for lat, lon in case_locations])
  clustering = DBSCAN(eps=0.1, min_samples=5).fit(coords)
  ```

- **Folium** - Interactive maps
  ```python
  import folium
  from folium.plugins import HeatMap
  
  m = folium.Map(location=[39.8, -98.5], zoom_start=4)
  HeatMap(case_coords).add_to(m)
  ```

**Use Case:** Interactive "Case Map" showing cold case clusters by region.

---

## 7. **Voice Cloning for Consistency** (Advanced)
**Goal:** Maintain consistent AI host voices across episodes.

### Tools:
- **Coqui TTS** - Open source text-to-speech with voice cloning
  ```python
  from TTS.api import TTS
  
  tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
  tts.tts_to_file(text="Welcome to Murder Index",
                  speaker_wav="maya_sample.wav",
                  file_path="output.wav")
  ```

**Use Case:** Generate consistent voice for Maya/Thorne without ElevenLabs costs.

---

## 8. **Image Enhancement for Old Case Photos**
**Goal:** Upscale and restore old/degraded victim photos.

### Tools:
- **Real-ESRGAN** - Super-resolution upscaling
  ```python
  from realesrgan import RealESRGANer
  
  upsampler = RealESRGANer(scale=4, model_path='RealESRGAN_x4plus.pth')
  output, _ = upsampler.enhance(input_img, outscale=4)
  ```

- **GFPGAN** - Face restoration
  ```python
  from gfpgan import GFPGANer
  
  restorer = GFPGANer(model_path='GFPGANv1.4.pth')
  _, restored_faces, _ = restorer.enhance(img)
  ```

**Use Case:** Restore 1980s victim photos for better visual presentation.

---

## Recommended Implementation Priority

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| 1 | Case Recommendations | Low | High |
| 2 | NER for Auto-Tagging | Medium | High |
| 3 | Topic Clustering | Medium | Medium |
| 4 | Audio Transcription | Low | High |
| 5 | Geographic Heatmaps | Low | Medium |
| 6 | Sentiment Analysis | Low | Medium |
| 7 | Image Enhancement | Medium | Medium |
| 8 | Voice Cloning | High | Low |

---

## Requirements Addition

Add to `requirements.txt`:
```
# ML/NLP
scikit-learn>=1.3.0
sentence-transformers>=2.2.0
spacy>=3.7.0
bertopic>=0.15.0
whisper-openai>=1.0.0
pyannote.audio>=3.1.0
textblob>=0.17.0
folium>=0.15.0

# Image Processing
realesrgan>=0.3.0
gfpgan>=1.3.0
```

Download spaCy model:
```bash
python -m spacy download en_core_web_lg
```
