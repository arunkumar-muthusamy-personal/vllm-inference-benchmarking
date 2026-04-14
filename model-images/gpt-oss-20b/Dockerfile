FROM alpine:3.19

WORKDIR /models

# Copy pre-downloaded model
COPY model/ /models/gpt-oss-20b/

# Optional: verify contents
RUN ls -lh /models/gpt-oss-20b