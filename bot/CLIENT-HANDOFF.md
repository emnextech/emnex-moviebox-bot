# Client Handoff

This file is the short version for the bot owner or client.

## What You Received

You now have a Telegram movie and TV download bot with two user tiers:

- BASIC users search titles and are sent to your website for downloads.
- PRO users get direct download links inside Telegram.

The bot is designed to help you:

- grow Telegram traffic
- send free users to your website
- sell PRO access
- manage upgrades manually from Telegram

## What BASIC Users Get

- Search for movies and TV shows
- See available quality options
- Click a button and open your website

This is the free funnel.

## What PRO Users Get

- Search for movies and TV shows
- Get direct links inside Telegram
- Access 1080p when available
- For TV shows, open a season and get episode links
- Use bulk episode links for the current chunk

This is the paid feature.

## Commands You Will Use

These commands work only for the owner account:

- `/grant <user_id> <days>`
- `/revoke <user_id>`
- `/user <user_id>`
- `/stats`

Examples:

```text
/grant 123456789 30
/revoke 123456789
/user 123456789
/stats
```

## How To Upgrade A User

1. Ask the user to open the bot and send `/plan`.
2. The bot will show their Telegram user ID.
3. After payment, open your bot and run:

```text
/grant <user_id> <days>
```

4. The user will become PRO immediately.

## What To Tell Your Users

Use this message:

```text
Send the movie or TV title in the bot.
Tap the correct result.
If you are on BASIC, the bot sends you to the website.
If you are on PRO, the bot gives you direct links in Telegram.
For series, choose a season, then an episode, or use Select All for the current chunk.
```

## Important Limits

- The bot works in private chat only.
- PRO activation is manual.
- Bulk episode delivery is limited per chunk for stability.
- If the movie API has no sources, the bot cannot create links.
- If the API is down or rate limited, users may see temporary errors.

## What To Do Daily

- Check the bot is online
- Grant PRO to paid users
- Revoke access if needed
- Use `/stats` to see basic activity

## When To Contact The Developer

Contact the developer if:

- the bot is offline
- free links open the wrong website
- PRO links are not appearing
- admin commands stopped working
- you want a new brand, new domain, or pricing changes

## Support Checklist

Before asking for help, collect:

- the affected Telegram username or user ID
- the movie or show title
- whether the user is BASIC or PRO
- a screenshot of the problem
- the time the issue happened
