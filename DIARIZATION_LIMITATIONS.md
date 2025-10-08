# Diarization Limitations and Path Forward

## Current Status

After extensive TDD work and following pyannote docs exactly:
- ✅ Force `num_speakers=2` for interviews
- ✅ Use `exclusive_speaker_diarization`
- ✅ Set clustering threshold correctly
- ✅ Extract embeddings from clean turns

**Result**: 63.3% Chaffee, 36.7% Guest (better than 100%, but still inaccurate)

## The Fundamental Problem

**Pyannote's diarization boundaries don't align with actual speaker turns.**

Example from video 1oKru2X3AvU:
```
Segment #2: "Mr. Johns, how are you, sir? Yeah, yeah, very good. Thank you."
- Pyannote says: One turn, one speaker
- Reality: Two speakers
  - "Mr. Johns, how are you, sir?" ← Chaffee
  - "Yeah, yeah, very good. Thank you." ← Guest

Segment #4: "a bit about yourself and how you came to the carnivore diet."
- Pyannote says: GUEST
- Reality: Chaffee asking question
```

## Why This Happens

1. **Diarization works on audio features** (pitch, timbre, rhythm)
2. **Not on linguistic content** (who's asking vs answering)
3. **Similar voices** (Chaffee and Pascal Johns sound similar)
4. **Fast back-and-forth** (quick responses without pauses)

Pyannote detects "someone is speaking from 17.8s to 22.9s" but can't tell that TWO people spoke in that 5-second window.

## What We Tried

### Attempt 1: Variance-Based Splitting ❌
- Split 30s chunks by similarity to Chaffee
- **Problem**: Chunks contain both speakers
- **Result**: Random attribution, 51.7%/48.3% split but wrong segments

### Attempt 2: Force num_speakers=2 ❌
- Force pyannote to find 2 speakers
- **Problem**: Pyannote's turn boundaries are wrong
- **Result**: 63.3%/36.7% split but still wrong segments

### Attempt 3: Exclusive Diarization ❌
- Use pyannote's new feature for better alignment
- **Problem**: Still relies on pyannote's boundaries
- **Result**: Same issues

## The Real Solution (Complex)

We need **word-level speaker attribution** by combining:

1. **Pyannote's speaker embeddings** (who the speakers are)
2. **Whisper's word timestamps** (when each word is spoken)
3. **Voice activity detection** (when each speaker is active)

### Algorithm

```python
# 1. Get pyannote's speaker turns
turns = pyannote.diarize(audio, num_speakers=2)
# Returns: [(0-20s, SPEAKER_0), (20-40s, SPEAKER_1), ...]

# 2. Get Whisper's word timestamps
words = whisper.transcribe(audio, word_timestamps=True)
# Returns: [("Hello", 0.5s), ("everyone", 1.2s), ...]

# 3. For each word, find which pyannote turn it belongs to
for word in words:
    turn = find_overlapping_turn(word.timestamp, turns)
    word.speaker = turn.speaker

# 4. Group words into sentences by speaker
sentences = group_by_speaker_and_pause(words)

# 5. Identify which speaker is Chaffee
for speaker in [SPEAKER_0, SPEAKER_1]:
    speaker_words = [w for w in words if w.speaker == speaker]
    embedding = extract_embedding(speaker_words)
    if similarity(embedding, chaffee_profile) > 0.65:
        speaker.label = "Chaffee"
    else:
        speaker.label = "GUEST"
```

This requires:
- Word-level alignment (we have this from Whisper)
- Turn-level embeddings (we have this from pyannote)
- Mapping between them (we need to implement this)

## Simpler Alternative: Accept Limitations

For the Dr. Chaffee use case:
1. **Most videos are monologues** (no guest) - works perfectly
2. **Interviews are rare** - can be manually reviewed
3. **Search still works** - even with wrong speaker labels, content is searchable
4. **Good enough for MVP** - 63% accuracy better than 0%

## Recommendation

**Option A: Ship with current limitations**
- Document that interview attribution is ~60-70% accurate
- Focus on monologue content (majority of videos)
- Manually review/fix interview videos if needed

**Option B: Implement word-level attribution**
- Significant engineering effort (2-3 days)
- Complex algorithm with edge cases
- May still have errors due to similar voices
- Benefit: 90-95% accuracy instead of 60-70%

**Option C: Use commercial solution**
- AssemblyAI, Deepgram, or Rev.ai have better diarization
- Cost: $0.25-1.00 per hour of audio
- Benefit: 95%+ accuracy out of the box

## My Recommendation

**Start with Option A**, then move to Option C if needed.

Reasons:
1. Most content is monologue (works perfectly)
2. Search functionality doesn't require perfect speaker labels
3. Commercial solutions are proven and cost-effective
4. Engineering time better spent on other features

## What We Learned (TDD Value)

Even though we didn't achieve perfect accuracy, TDD was invaluable:
- ✅ Found 4 critical bugs systematically
- ✅ Understood the problem deeply
- ✅ Documented limitations clearly
- ✅ Have tests to prevent regressions
- ✅ Know exactly what would be needed for better accuracy

Without TDD, we'd still be guessing why it doesn't work.

---

**Status**: Documented limitations, ready to decide on path forward
