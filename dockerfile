FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    wget curl unzip gnupg ca-certificates fonts-liberation libasound2 \
    libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 \
    libnspr4 libnss3 libx11-xcb1 libxcomposite1 libxdamage1 \
    libxrandr2 xdg-utils libu2f-udev libvulkan1 libharfbuzz0b \
    libglib2.0-0 libgbm1 libgtk-3-0 --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

RUN wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/125.0.6422.113/linux64/chrome-linux64.zip && \
    unzip chrome-linux64.zip && \
    mv chrome-linux64 /opt/chrome && \
    ln -s /opt/chrome/chrome /usr/bin/google-chrome && \
    rm chrome-linux64.zip

RUN wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/125.0.6422.113/linux64/chromedriver-linux64.zip && \
    unzip chromedriver-linux64.zip && \
    mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf chromedriver-linux64.zip chromedriver-linux64

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "./bot.py"]
