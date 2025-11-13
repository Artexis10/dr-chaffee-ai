# Custom Instructions - Quick Start Guide

## What Is This?

A simple way to tune the AI's responses **without touching any code or breaking safety rules**.

Think of it like this:
- **Baseline Rules** (Hidden) = Core medical accuracy, persona, safety guardrails
- **Your Custom Instructions** (Editable) = Your preferences for tone, depth, emphasis, etc.

The AI always follows baseline rules first, then adds your custom guidance on top.

---

## How to Use (3 Steps)

### 1. Open the Tuning Dashboard
Go to: **http://localhost:3000/tuning**

Look for the **"Custom Instructions"** section at the top.

### 2. Create Your First Instruction Set

Click **"New Instruction Set"**

Fill in:
- **Name**: Something descriptive (e.g., "Enhanced Medical Focus")
- **Description**: What these instructions do (optional)
- **Instructions**: Your guidance in plain English

Example:
```
- Emphasize autoimmune conditions when relevant
- Use more technical medical terminology
- Always cite video timestamps for every claim
- Keep answers under 200 words unless asked for detail
```

### 3. Preview & Save

Click **"Preview Merged Prompt"** to see how it combines with baseline rules.

Click **"Save Instructions"** when ready.

Check **"Activate immediately"** to use it right away.

---

## Example Use Cases

### Make Answers More Technical
```
Name: Healthcare Professional Mode

Instructions:
- Use medical terminology (e.g., "hyperinsulinemia" not "high insulin")
- Include mechanism of action details
- Reference clinical markers and lab values
- Cite studies with PMID when available
```

### Emphasize Specific Topics
```
Name: Autoimmune Focus

Instructions:
- Prioritize autoimmune condition context
- Emphasize elimination protocols
- Reference clinical outcomes for autoimmune patients
- Use terms like "autoimmune protocol", "elimination phase"
```

### Control Answer Length
```
Name: Concise Mode

Instructions:
- Keep answers under 150 words unless explicitly asked for detail
- Lead with the direct answer first
- Use bullet points for multiple points
- Avoid lengthy explanations
```

### Better Citations
```
Name: Enhanced Citations

Instructions:
- Always include video title and timestamp
- Prefer citing multiple sources when available
- Note when extrapolating beyond direct quotes
- Mention if topic has limited coverage
```

---

## Managing Instruction Sets

### Switch Between Sets
1. Go to tuning dashboard
2. Find the instruction set you want
3. Click **"Activate This Set"**
4. Changes take effect immediately (no restart needed)

### Edit Existing Set
1. Click the **edit icon** (📄) next to the instruction set
2. Make your changes
3. Click **"Preview"** to see the result
4. Click **"Save"**

### View History
1. Click the **history icon** (🕐) next to any instruction set
2. See all previous versions with timestamps
3. Click **"Rollback"** to restore an old version

### Delete a Set
1. Click the **trash icon** (🗑️) next to the instruction set
2. Confirm deletion
3. Note: Cannot delete the "default" set

---

## Tips & Best Practices

✅ **Start Simple** - Add 2-3 instructions, test, then refine  
✅ **Use Preview** - Always preview before saving to see the merged result  
✅ **Be Specific** - "Emphasize X" is better than "Be more detailed"  
✅ **Test Queries** - Try a few questions to see if instructions work as expected  
✅ **Use History** - Don't worry about breaking things - you can always rollback  

❌ **Don't Contradict Baseline** - Can't override core safety rules  
❌ **Don't Overload** - Too many instructions (>1000 words) may dilute effectiveness  
❌ **Don't Use Code** - Plain English only, no programming syntax  

---

## Character Limits

- **Name**: 255 characters max
- **Description**: 500 characters max
- **Instructions**: 5000 characters max (~1000 words)

The UI shows a character counter as you type.

---

## What You Can Control

✅ **Tone** - Technical vs conversational, formal vs casual  
✅ **Depth** - Brief vs detailed, summary vs deep dive  
✅ **Emphasis** - Which topics to prioritize  
✅ **Citations** - How to format and present sources  
✅ **Structure** - Bullet points vs paragraphs, length preferences  
✅ **Terminology** - Medical terms vs layman's terms  

❌ **Cannot Override** - Core persona, medical accuracy rules, safety guardrails  

---

## Troubleshooting

**Q: I saved instructions but don't see any change in responses**  
A: Make sure the instruction set is marked as "Active" (green badge). Only one set can be active at a time.

**Q: Preview shows an error**  
A: Check that your instructions don't exceed 5000 characters. Try shortening them.

**Q: Can I have multiple instruction sets active?**  
A: No, only one at a time. But you can switch between them instantly.

**Q: What happens if I delete all my instruction sets?**  
A: The "default" set (empty instructions) will remain. The AI will use baseline rules only.

**Q: Can I export/import instruction sets?**  
A: Not yet, but you can copy/paste the text between sets manually.

---

## Need Help?

- **Full Documentation**: See `CUSTOM_INSTRUCTIONS_GUIDE.md`
- **API Reference**: All endpoints documented in the guide
- **Technical Details**: Architecture and code locations in the guide

---

## Summary

Custom instructions let you tune the AI's behavior safely and easily:

1. **Open** http://localhost:3000/tuning
2. **Create** a new instruction set with your preferences
3. **Preview** to see how it merges with baseline rules
4. **Save & Activate** to start using it immediately
5. **Iterate** - Edit, test, rollback as needed

The baseline safety rules are always protected. Your custom instructions are additive only.

**Remember**: You can't break anything. Version history lets you rollback anytime.
