
# Galactus Telegram Bot

This is a Telegram bot powered by Python, OpenAI, and Docker. The bot provides functionalities like fetching Marvel Snap deck information, interacting with users via inline buttons, and monitoring updates from a website.

## Requirements

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/rogercezidio/galactus_bot.git
cd galactus_bot
```

### 2. Environment Configuration

Create two `.env` files: one for development and one for production.

- `.env.dev`: (for development)
    ```bash
    BOT_TOKEN=your-development-bot-token
    OPENAI_API_KEY=your-development-openai-api-key
    GALACTUS_CHAT_ID=your-group-chat-id
    ```

- `.env.prod`: (for production)
    ```bash
    BOT_TOKEN=your-production-bot-token
    OPENAI_API_KEY=your-production-openai-api-key
    GALACTUS_CHAT_ID=your-group-chat-id
    ```

Also create a `.env` with the same content as `.env.prod`.

Ensure your `.env` files are in the root of the project directory and **do not commit them** to version control (add them to `.gitignore`).

### 3. Docker Compose

#### Docker Compose Configuration

Ensure your `docker-compose.yml` file looks like this:

```yaml
services:
  my-bot:
    build: . 
    volumes:
      - ./app/data:/app/data
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GALACTUS_CHAT_ID=${GALACTUS_CHAT_ID}
```

This allows you to dynamically select the environment file when starting the bot.

#### Run the Bot in Development

To start the bot in **development**, run:

```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml up
```

#### Run the Bot in Production

To start the bot in **production**, run:

```bash
docker-compose up -d
```

### 4. Persisting Data Between Container Restarts

Ensure that the `last_update.txt` file persists between container restarts by mounting a volume.

- The file is stored at `./app/data/last_update.txt` inside the container.
- Use Docker volumes to persist the data across container restarts.

### 5. Managing Containers

To bring up the bot container (either in dev or prod) with Docker Compose:

```bash
docker-compose up -d
```

To stop the bot:

```bash
docker-compose down
```

To view logs:

```bash
docker-compose logs -f
```

## Automatic Restart on EC2 Reboot

To ensure the bot automatically starts after an EC2 instance reboots, you can use **systemd** on your EC2 instance to manage the Docker Compose service.

### Step 1: Create a systemd Service File

Create a new service file for systemd to manage your Docker Compose application.

```bash
sudo nano /etc/systemd/system/galactus-bot.service
```

Add the following content to the file:

```ini
[Unit]
Description=Galactus Telegram Bot
After=docker.service
Requires=docker.service

[Service]
Restart=always
WorkingDirectory=/path/to/your/project
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down

[Install]
WantedBy=multi-user.target
```

Replace `/path/to/your/project` with the actual path to your bot's project directory.

### Step 2: Enable and Start the Service

Run the following commands to enable the service so it starts automatically on reboot:

```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable galactus-bot

# Start the service
sudo systemctl start galactus-bot
```

Now, your Docker Compose application will automatically start when your EC2 instance reboots.

### Step 3: Verify the Service

You can check the status of the service with:

```bash
sudo systemctl status galactus-bot
```

## Troubleshooting

- **Docker Not Found Error**: Ensure Docker is installed and running. Use `docker ps` to verify.
- **Environment File Missing**: Make sure the correct `.env` file is created and included in the `docker-compose.yml`.
- **Bot Not Starting After Reboot**: Ensure the systemd service is enabled with `sudo systemctl enable galactus-bot`.

## Additional Commands

- **Restart the bot manually**:
    ```bash
    sudo systemctl restart galactus-bot
    ```

- **View systemd logs**:
    ```bash
    sudo journalctl -u galactus-bot
    ```

## Contributing

Feel free to fork this repository and create pull requests to add new features or fix bugs.

---

### Author:
Roger Cezidio
