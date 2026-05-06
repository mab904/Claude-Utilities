# AI Parliament

Alright, let me explain what this is about and how it's put together.

The idea is simple: 6 AIs with different personalities (based on MBTI) live their lives on a screen, wander around, talk to each other, and when you type a question, they're summoned to parliament, debate, and vote. All running on a local language model on your own machine.

## Why I built this

The real goal was to experiment with local AIs and see a few things:

- Whether the models were fast enough to do something in real time, or whether the wait would be unbearable
- What kind of response quality you get when you give them a role and some context
- Whether they actually "listen" to what the other AIs say or just ignore the debate history
- Whether there'd be too much consensus (spoiler: yes, they tend to agree a lot)
- Whether the MBTI personalities show up in the responses, or it all sounds the same
- Recently I've seen AI agent simulations getting a lot of traction and I wanted to give it a try.

Short answer: it works, it's interesting, but it has some pretty clear limitations that I cover further down.

## The 6 agents

Each one has a color, a personality, and a fixed spot on the map where they live.

| Color | Name | MBTI | Role |
|---|---|---|---|
| Blue | Aris | INTP | The Architect — analytical, logical |
| Yellow | Nova | ENFP | The Visionary — creative, enthusiastic |
| Gray | Doctore | ISTJ | The Inspector — data, evidence |
| Red | Kaito | ENTJ | The Commander — strategic, direct |
| Purple | Lyra | INFJ | The Prophet — intuitive, holistic |
| Orange | Naranjito | ESFP | The Cheerleader — practical, social |

Each one's `system_prompt` tells them who they are, how they talk, and what phrases they use. That's what makes Aris say "logically..." and Naranjito say "let's get to the point!". If you want to change someone's personality, you edit that text in `config.py`.

## Setup

```bash
# 1. Install Ollama from https://ollama.com
ollama serve                       # leave it running in another terminal
ollama pull llama3.2               # the model the AIs use (~2 GB)
ollama pull nomic-embed-text       # optional, for semantic memory (~270 MB)

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Run it
python main.py
```

If your machine can handle bigger models, change `OLLAMA_MODEL` in `config.py`. With `qwen2.5:7b` or `mistral` the responses are noticeably better, though slower. That's why I stick with the lighter model by default — otherwise it takes too long.

## Controls

There's not much:

| Action | Key |
|---|---|
| Summon parliament | Type your question + **ENTER** |
| Toggle voice on/off | **F2** |
| Interrupt parliament | **ESC** |
| Scroll panels | **Mouse wheel** |

## The phases of parliament

When you type a question, here's what happens, in order:

**A. Summoning** — The 6 AIs walk toward the central circle.

**B. Internal thinking** — Each one privately generates their reflection on the question. This runs in parallel, so all 6 think at once. Nothing is said out loud and the others can't see it.

**C. External debate** — They speak in turns. Each AI sees the history of what the previous ones have said and can respond. This part is sequential (one waits for the other), which is what makes it slow.

**E. Final stance** — Each one summarizes their definitive position before voting. Parallel.

**F. Voting** — They vote FOR or AGAINST. Parallel.

**G. Result** — A "secretary" (another LLM call) synthesizes the debate and gives the result. Shown in green on the panel.

**H. Dispersal** — They go back to their homes and resume their daily lives.

## How the code is laid out

```
main.py           → the main pygame loop, events, drawing
config.py         → all the settings and the MBTI profiles for each agent
agent.py          → each AI: state, movement, animation, LLM calls
parliament.py     → orchestrates phases A-H
ollama_client.py  → makes the HTTP requests to Ollama with auto-retries
ui.py             → side panels, text box, header and footer
memory.py         → saves parliaments to JSON and retrieves them by relevance
tts.py            → local voice with pyttsx3, serial queue so they don't overlap
```

LLM calls don't block the animation because each agent fires off a `threading.Thread` whenever it needs to generate text. The pygame loop keeps running at 60 FPS while Ollama works.

## Memory across sessions

When each parliament ends, what each agent said, how they voted, and the final consensus get saved to `parliament_memory.json`. The next time there's a parliament on a similar topic, each AI gets a summary in its prompt of what it said before.

The relevant-memory search works in three modes depending on what you have installed:

- **Semantic** — uses vector embeddings (`nomic-embed-text`). Finds similar topics even if they use different words.
- **Keyword** — Jaccard over keywords. More basic but doesn't need anything extra.
- **Recent** — just the last N parliaments. Always works.

It's auto-detected at startup. If you install `nomic-embed-text` later, it computes the embeddings for the old entries in the background.

## The voice

Each agent has a system voice index and a different speed. Aris speaks slowly and thoughtfully, Naranjito speaks fast. On Windows it uses SAPI5 (whatever voices you have installed). On macOS it uses NSSpeechSynthesizer.

What gets spoken out loud: casual greetings, debate interventions, final stances, voting reasons.

What doesn't get spoken: internal thoughts (private by design) and the secretary's consensus.

The voice queue is serial, so even though the LLMs generate responses in parallel, the voices play one after another without overlapping.

## Visual indicators

Each agent has a **colored dot** in the bottom-left corner showing their state:

- Dark gray → resting at home
- Green → wandering
- Yellow → approaching another agent
- Cyan → casual conversation
- Red → moving to parliament
- Bright purple → thinking internally
- Bright yellow → debating
- Orange → voting
- Light green → going home

When they're thinking (waiting for an LLM response), **3 blinking yellow dots** appear above the name.

The **pulsing ring** around the body shows up when they're active in something: conversation, debate, thinking, or voting. The ring's color changes depending on the phase.

## Drawbacks

This part is important because if you're going to use it, you should know what you're getting into.

**The models are slow.** Ollama runs locally and is free, but on a normal CPU each response can take between 5 and 20 seconds. A full parliament can take 2–3 minutes. With a GPU it's much faster. This is the biggest limitation, by far.

**There are timeouts.** When 6 agents call Ollama in parallel, Ollama processes them one at a time internally. The last one in line can wait 90 seconds just queuing, plus generation time. If the model is slow that day, it goes over the timeout. There are auto-retries (up to 3 attempts at 180 seconds each), but if Ollama is heavily loaded it can fail anyway. In the phases before the debate it doesn't matter much, but in the final-stance phase there's a fallback that uses what the agent said during the debate as their stance.

**The voices sometimes don't play.** pyttsx3 with SAPI5 on Windows has a known bug where after the first utterance the engine accumulates internal state and the next ones fail silently. I tried to fix it by reinitializing the engine for each phrase, but on some systems it can still be unstable. If you don't hear anything after the first agent, that's why.

**Text sometimes gets cut off.** The model generates up to a token limit. If a sentence is long and hits the limit, it gets cut mid-sentence. I bumped up the tokens to reduce it, but it doesn't disappear completely without slowing things down a lot more.

**Too much consensus.** The models tend to reach agreement. There are rarely truly heated debates. In general they all end up backing some version of the same idea. This is a limitation of the model, not the code. It's usually 5-to-1 for or against.

**The personalities barely show with small models.** With `llama3.2:3b` the differences between agents are subtle. With bigger models (`qwen2.5:7b`, `mistral`) the MBTI personalities come through much more clearly in the tone and the kind of arguments.

**No real interaction between agents outside parliament.** During daily life they walk up to each other and say hi, but there's no memory of those conversations and they don't influence parliament. Each agent is independent except for the debate history that gets injected into the prompt.

## Quick configuration

Everything tweakable lives in `config.py`:

- `DEBATE_ROUNDS` — debate rounds (1 by default, more rounds = slower but more realistic)
- `MEMORY_RECALL_N` — how many past parliaments each agent receives in the prompt
- `MEMORY_RECALL_MODE` — `"auto"`, `"semantic"`, `"keyword"` or `"recent"`
- `OLLAMA_MODEL` — the model all agents use
- `TTS_ENABLED_DEFAULT` — whether voice starts on or off

To wipe memory and start fresh, delete `parliament_memory.json`.

## Ideas left on the table

- The graphics are very pixelated. I tried to clean it up with Claude but it's still not crisp.
- Visual coalitions: have the AIs cluster before voting based on affinity
- Rebel mode: let an agent oppose the consensus if their conviction is strong enough
- Export parliaments as a browsable HTML
- A panel showing which past memories are influencing the current parliament
