FROM ubuntu:latest
COPY install.sh /install.sh
RUN chmod +x /install.sh && /install.sh
# Simple Ubuntu Docker image
# You can add more instructions here as needed
