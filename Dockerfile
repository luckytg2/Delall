# Use official Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Environment variables (use docker-compose or runtime for actual values)
ENV BOT_TOKEN=7843411053:AAEfr-VOWHgMWV5HmLVbaoFrF4rh5gM-Ybg

# Run the bot
CMD ["python", "bot.py"]
