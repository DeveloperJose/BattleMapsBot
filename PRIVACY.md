# AWBW BattleMaps v2 Privacy Policy

**Last updated: November 25, 2026**

AWBW BattleMaps v2 is a Discord application that provides a bot for the Advance Wars By Web (AWBW) community. This policy explains what the bot processes when people use it.

## Information the bot processes

- **Messages containing map links:** The bot reads message content in channels and threads where it has access to identify AWBW map-preview links. It extracts the map ID to make a preview. The application does not intentionally save or archive message content.
- **Command and component inputs:** The bot processes map IDs, game IDs, replay positions, and AWBW usernames supplied to its slash commands. It also receives interaction and channel information from Discord to respond and apply channel posting limits.
- **AWBW data:** To fulfill requests, the bot requests public map, game, analysis, profile, and league information from AWBW. A requested map ID, game ID, or username may be sent to AWBW as part of those requests.
- **Operational statistics:** The bot stores aggregate counts and request/render timings to monitor performance. Some operational records include a map or game ID for the slowest render. These statistics do not contain message text.

## Local caches and retention

The bot stores data in local SQLite databases to reduce repeat requests to AWBW. Map data is cached for up to 24 hours, profile data for up to 6 hours, and public league standings for up to 24 hours. Map-analysis data is cached in memory for up to 6 hours. Cache entries may be removed earlier during cache cleanup.

Operational counters are stored locally and currently have no automatic deletion period. They contain usage totals and timing information, not Discord message text. Access to the bot's host and database is limited to its operators.

## How information is used

The bot uses the information above to create the requested preview or profile response, reduce duplicate AWBW requests, enforce channel posting limits, and monitor service performance. The application does not use message content to train AI or machine-learning models and does not sell user data.

## Third-party services

Discord delivers messages and interactions to the bot under Discord's own terms and privacy policy. AWBW provides the public game data requested by the bot and applies its own policies to those requests. AWBW BattleMaps v2 is an independent community application and is not operated by AWBW.

## Questions or requests

For privacy questions or requests concerning data held by this application, contact the application operator, DevJ, through the contact method listed on the application's public profile. Requests can identify the relevant AWBW username or map/game ID. Cached records expire according to the retention periods above; operational aggregates may not identify an individual user.

## Changes

This policy may be updated when the application's behavior changes. The current version will be published at the application's Privacy Policy URL.
