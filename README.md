# Watchman

![](https://primetime.james.gg/images/watchman.png)

## Installation

### Hosted
https://discord.com/api/oauth2/authorize?client_id=539224624815276040&permissions=128&scope=bot

Add the bot to your server and in a channel only server administrators can see, use `!wm`.

Note: If you choose not to grant the bot permissions to view audit logs, bans for your server will be logged as made by "Unknown" for reason "Unknown".

### Self-Hosted
Watchman makes heavy use of PostgreSQL. The database situation in v1 is not sophisticated: you'll need a database called watchman and a user called watchman to connect to the database. This could be easily modified, see [watchman.py](src/cogs/watchman.py).

See [watchman.service](watchman.service) for an example systemd service file.

## Commands

All commands will only work in the watchman channel. If a command takes a [User/Name+Discriminator/ID] as a parameter and multiple users have that name (e.g. "James"),
it may be worth specifying the discriminator or ID. See the examples for more. 

### !wm
Makes the current channel the watchman channel. All other commands must be called in a watchman channel, and they won't work anywhere until you use this command.

Syntax: `!wm`

### !docs
Returns a link to this page.

Syntax: `!docs`

### !note
Add a note about a user. Notes must be no more than 150 characters.

Notes are not about reasons to ban a user but are there to inform other server administrators of past actions.

Keep in mind the date displayed next to the note and its contents - users do change and some people find different levels of behaviour appropriate.

Syntax: `!note [User/Name+Discriminator/ID] [Note]`
```
Example 1: !note James#0304 continuing to engage in behaviour that is not conducive to the desired environment

Example 2: !note James continuing to engage in behaviour that is not conducive to the desired environment

Example 3: !note 402081103923380224 continuing to engage in behaviour that is not conducive to the desired environment
```

### !unnote
Removes your note for a user for the server it's used in.

Syntax: `!unnote [User/Name+Discriminator/ID]`
```
Example 1: !unnote James#0304

Example 2: !unnote James

Example 3: !unnote 402081103923380224
```
### !info
Shows all bans and notes for a user across all servers.

Syntax: `!info [User/Name+Discriminator/ID]`
```
Example 1: !info James#0304

Example 2: !info James

Example 3: !info 402081103923380224
```

## Listeners

### When the bot joins:
When the bot joins a new server and has access to the audit log, it will record all past bans.

### When a member joins:
When a member joins your server and has bans or notes in other servers, that information will be displayed in the watchman channel.

### When a member is banned in another server:
When a member is banned in another server, that information will be displayed in the watchman channel.

### When a member is banned in your server:
If you ban a user, make sure to add a sensible reason so that information is relayed. Banning users for "yeet" isn't very useful without context, even if deserved.

A ban message won't be sent to the server the user was banned from.

### When a member has a note made about them in another server:
When a member has a note made about them in another server, that information will be displayed in the watchman channel.

### When a member has a note made about then in your server:
If you make a note about a user, make sure it has as much context as you would want out of 150 characters. Try to avoid using derogatory language.

