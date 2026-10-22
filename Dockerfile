FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY bot/requirements.txt /app/bot/requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r /app/bot/requirements.txt \
    && python -m pip install --no-cache-dir "supabase==2.23.0"

COPY bot /app/bot

CMD ["python", "-m", "bot.main"]
