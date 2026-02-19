#!/bin/sh
ollama serve &
OLLAMA_PID=$!
sleep 5

# Pull the model
ollama pull mistral

wait $OLLAMA_PID
