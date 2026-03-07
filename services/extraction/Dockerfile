FROM ollama/ollama:latest

COPY start.sh /start.sh
RUN chmod +x /start.sh

ENV OLLAMA_HOST=0.0.0.0:11434

EXPOSE 11434

ENTRYPOINT ["/start.sh"]