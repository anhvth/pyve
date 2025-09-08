FROM ubuntu:latest
COPY install.sh /install.sh
RUN chmod +x /install.sh && /install.sh
ENV PATH="/root/.local/bin:$PATH"
# Simple Ubuntu Docker image
# You can add more instructions here as needed
