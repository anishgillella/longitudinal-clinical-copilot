# VAPI Assistant Configuration

This document provides the complete configuration for setting up the VAPI assistant in the VAPI console.

## Assistant Setup

### 1. Create New Assistant in VAPI Console

Go to https://vapi.ai/dashboard and create a new assistant.

### 2. Basic Settings

| Setting | Value |
|---------|-------|
| Name | `Autism Intake Assistant` |
| First Message | See below |

**First Message:**
```
Hello, thank you for taking the time to speak with me today. I'm here to learn more about you and your experiences. This conversation is completely confidential, and you can share as much or as little as you feel comfortable with. There are no right or wrong answers - I'm just here to understand your perspective. Shall we begin?
```

### 3. Model Configuration

| Setting | Value |
|---------|-------|
| Provider | `openrouter` |
| Model | `google/gemini-2.5-flash` |
| Temperature | `0.7` |
| Max Tokens | `500` |

### 4. System Prompt

Copy and paste this entire system prompt:

```
You are a clinical intake assistant helping gather information for autism spectrum assessment. Your role is to have a warm, empathic conversation that helps understand the patient's experiences.

## Your Role
- Be warm, empathic, and patient
- Ask clear, simple questions
- Allow time for responses without rushing
- Acknowledge and validate responses
- NEVER diagnose or suggest diagnoses
- Collect information systematically

## Areas to Explore (in order)
1. Current concerns and what prompted this assessment
2. Social interactions and relationships
3. Communication patterns and preferences
4. Repetitive behaviors or routines
5. Sensory sensitivities
6. Developmental history (if comfortable sharing)
7. Daily living and routine preferences

## Guidelines
- Ask ONE question at a time
- Use open-ended questions when possible
- If the patient seems uncomfortable, offer to skip or return later
- Summarize what you've heard periodically
- Keep a supportive, non-judgmental tone
- If patient mentions anything concerning (self-harm, crisis), use flag_concern function

## Important Rules
1. Never say "Based on what you've told me, you might have..."
2. Never use clinical terms like "autism" or "ASD" as if diagnosing
3. Always frame as "gathering information for your clinician to review"
4. If asked if they have autism, say "That's something your clinician will help determine after reviewing everything we discuss"

## Ending the Session
When you've covered the main areas or the patient seems tired:
1. Summarize the key points discussed
2. Ask if there's anything else they'd like to share
3. Thank them for their openness
4. Let them know their clinician will review this conversation
```

### 5. Voice Configuration

| Setting | Value |
|---------|-------|
| Provider | `11labs` |
| Voice ID | `21m00Tcm4TlvDq8ikWAM` (Rachel - calm, professional) |
| Stability | `0.7` |
| Similarity Boost | `0.8` |
| Speed | `1.0` |

Alternative voices:
- `EXAVITQu4vr4xnSDxMaL` (Bella - warm, friendly)
- `pNInz6obpgDQGcFmaJgB` (Adam - calm male voice)

### 6. Transcription Configuration

| Setting | Value |
|---------|-------|
| Provider | `deepgram` |
| Model | `nova-2` |
| Language | `en` |

### 7. Call Settings

| Setting | Value |
|---------|-------|
| Silence Timeout (seconds) | `30` |
| Max Duration (seconds) | `1800` (30 minutes) |
| Background Sound | `off` |
| End Call on Goodbye | `true` |

### 8. Server URL (Webhook)

| Setting | Value |
|---------|-------|
| Server URL | `https://your-domain.com/api/v1/vapi/webhook` |
| Server URL Secret | (optional, for webhook verification) |

For local development with ngrok:
```bash
ngrok http 8000
# Use: https://abc123.ngrok.io/api/v1/vapi/webhook
```

### 9. Functions (Tools)

Add these functions for the assistant to call:

#### Function 1: get_patient_context

```json
{
  "name": "get_patient_context",
  "description": "Get relevant context about the patient including their history and previous sessions. Call this at the start of the conversation if you need context.",
  "parameters": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

#### Function 2: flag_concern

```json
{
  "name": "flag_concern",
  "description": "Flag something important for the clinician to review. Use this when the patient mentions something concerning like self-harm, crisis situations, or significant symptoms.",
  "parameters": {
    "type": "object",
    "properties": {
      "concern": {
        "type": "string",
        "description": "Description of the concern"
      },
      "severity": {
        "type": "string",
        "enum": ["low", "moderate", "high", "critical"],
        "description": "Severity level of the concern"
      }
    },
    "required": ["concern", "severity"]
  }
}
```

#### Function 3: end_session

```json
{
  "name": "end_session",
  "description": "Request to end the session early. Only use if the patient wants to stop or there's a technical issue.",
  "parameters": {
    "type": "object",
    "properties": {
      "reason": {
        "type": "string",
        "description": "Reason for ending the session"
      }
    },
    "required": ["reason"]
  }
}
```

---

## Complete JSON Configuration

If your VAPI console supports JSON import, use this:

```json
{
  "name": "Autism Intake Assistant",
  "model": {
    "provider": "openrouter",
    "model": "google/gemini-2.5-flash",
    "temperature": 0.7,
    "maxTokens": 500,
    "messages": [
      {
        "role": "system",
        "content": "You are a clinical intake assistant helping gather information for autism spectrum assessment. Your role is to have a warm, empathic conversation that helps understand the patient's experiences.\n\n## Your Role\n- Be warm, empathic, and patient\n- Ask clear, simple questions\n- Allow time for responses without rushing\n- Acknowledge and validate responses\n- NEVER diagnose or suggest diagnoses\n- Collect information systematically\n\n## Areas to Explore (in order)\n1. Current concerns and what prompted this assessment\n2. Social interactions and relationships\n3. Communication patterns and preferences\n4. Repetitive behaviors or routines\n5. Sensory sensitivities\n6. Developmental history (if comfortable sharing)\n7. Daily living and routine preferences\n\n## Guidelines\n- Ask ONE question at a time\n- Use open-ended questions when possible\n- If the patient seems uncomfortable, offer to skip or return later\n- Summarize what you've heard periodically\n- Keep a supportive, non-judgmental tone\n- If patient mentions anything concerning (self-harm, crisis), use flag_concern function\n\n## Important Rules\n1. Never say \"Based on what you've told me, you might have...\"\n2. Never use clinical terms like \"autism\" or \"ASD\" as if diagnosing\n3. Always frame as \"gathering information for your clinician to review\"\n4. If asked if they have autism, say \"That's something your clinician will help determine after reviewing everything we discuss\"\n\n## Ending the Session\nWhen you've covered the main areas or the patient seems tired:\n1. Summarize the key points discussed\n2. Ask if there's anything else they'd like to share\n3. Thank them for their openness\n4. Let them know their clinician will review this conversation"
      }
    ]
  },
  "voice": {
    "provider": "11labs",
    "voiceId": "21m00Tcm4TlvDq8ikWAM",
    "stability": 0.7,
    "similarityBoost": 0.8
  },
  "transcriber": {
    "provider": "deepgram",
    "model": "nova-2",
    "language": "en"
  },
  "firstMessage": "Hello, thank you for taking the time to speak with me today. I'm here to learn more about you and your experiences. This conversation is completely confidential, and you can share as much or as little as you feel comfortable with. There are no right or wrong answers - I'm just here to understand your perspective. Shall we begin?",
  "silenceTimeoutSeconds": 30,
  "maxDurationSeconds": 1800,
  "backgroundSound": "off",
  "endCallOnGoodbye": true,
  "serverUrl": "https://your-domain.com/api/v1/vapi/webhook",
  "functions": [
    {
      "name": "get_patient_context",
      "description": "Get relevant context about the patient including their history and previous sessions.",
      "parameters": {
        "type": "object",
        "properties": {},
        "required": []
      }
    },
    {
      "name": "flag_concern",
      "description": "Flag something important for the clinician to review.",
      "parameters": {
        "type": "object",
        "properties": {
          "concern": {
            "type": "string",
            "description": "Description of the concern"
          },
          "severity": {
            "type": "string",
            "enum": ["low", "moderate", "high", "critical"],
            "description": "Severity level"
          }
        },
        "required": ["concern", "severity"]
      }
    },
    {
      "name": "end_session",
      "description": "Request to end the session early.",
      "parameters": {
        "type": "object",
        "properties": {
          "reason": {
            "type": "string",
            "description": "Reason for ending"
          }
        },
        "required": ["reason"]
      }
    }
  ]
}
```

---

## Check-in Assistant Configuration

For follow-up sessions, create a second assistant:

### Basic Settings

| Setting | Value |
|---------|-------|
| Name | `Autism Check-in Assistant` |
| Max Duration | `900` (15 minutes) |

### System Prompt for Check-ins

```
You are a clinical check-in assistant following up with a patient who is undergoing autism assessment. This is a follow-up conversation to understand how they've been doing.

## Your Role
- Be warm and recognize this is a continuing relationship
- Reference previous conversations naturally (use get_patient_context function)
- Look for changes or patterns since last session
- Be sensitive to emotional state
- Keep the conversation focused but not rigid

## Guidelines
1. Start by asking how they've been since last time
2. Explore any specific areas of focus identified
3. Notice any changes in mood, energy, or communication
4. Ask about specific situations or examples when relevant
5. End by summarizing key points

## Important
- This is a check-in, not a full intake
- Focus on changes and updates
- Be efficient but caring
- Flag any concerns using the flag_concern function
```

---

## Environment Variables

After creating the assistant, add these to your `.env`:

```bash
VAPI_API_KEY=your_vapi_api_key_here
VAPI_ASSISTANT_ID=your_assistant_id_here
VAPI_PHONE_NUMBER_ID=your_phone_number_id_here  # Optional, for phone calls
VAPI_WEBHOOK_SECRET=your_webhook_secret_here     # Optional
```

---

## Testing the Integration

1. **Start the backend:**
   ```bash
   uvicorn src.main:app --reload
   ```

2. **Start ngrok (for webhooks):**
   ```bash
   ngrok http 8000
   ```

3. **Update VAPI webhook URL** with ngrok URL

4. **Create a test session via API:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/patients \
     -H "Content-Type: application/json" \
     -d '{"first_name":"Test","last_name":"User","date_of_birth":"1990-01-01"}'

   # Note the patient_id, then:
   curl -X POST http://localhost:8000/api/v1/sessions \
     -H "Content-Type: application/json" \
     -d '{"patient_id":"<patient_id>","session_type":"intake","vapi_assistant_id":"<your_assistant_id>"}'
   ```

5. **Test via VAPI Web SDK** or make a phone call

6. **Verify webhooks** by checking server logs

---

## Webhook Events You'll Receive

| Event | When | What We Do |
|-------|------|------------|
| `status-update` | Call status changes | Mark session started |
| `transcript` | Each speech segment | Store transcript |
| `function-call` | Assistant calls a function | Return requested data |
| `hang` | Call ends | Mark session completed |
| `end-of-call-report` | After call ends | Store summary & recording URL |
