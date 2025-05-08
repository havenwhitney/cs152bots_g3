# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
import pdb

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.under_review = {} # Map from report message IDs to the report
        self.reacts = { # valid reacts for the bot to respond to
            '🔨': 'ban',
            '⚠️': 'warn',
            '❌': 'ignore',
        }
        

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
        

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            # Send report information to mod channel for further action
            complete_report = self.reports.pop(author_id)
            # print(self.mod_channels)
            mod_channel = self.mod_channels[complete_report.guild_id] # CHANGE
            reported_msg = complete_report.message
            # print(reported_msg)
            
            report_data = []
            report_data.append(f"Report from {message.author.name} ({message.author.id})")
            report_data.append(f"Message: \n```{reported_msg.content}\n```")
            report_data.append(f"Reason: {complete_report.reason}")
            report_data.append(f"Category: {complete_report.category}")
            if complete_report.should_block:
                report_data.append("User has requested to block this user from contacting them further.")
            else:
                report_data.append("User has not requested to block this user from contacting them further.")
            report_data.append("Report complete. \n")
            report_data.append("If you would like to see the message in context, click on the link below:")
            report_data.append(f"https://discord.com/channels/{complete_report.guild_id}/{reported_msg.channel.id}/{reported_msg.id}\n")
            report_data.append("To take action, react to this message with one of the following:")
            report_data.append("🔨 to ban the user")
            report_data.append("⚠️ to warn the user")
            report_data.append("❌ to ignore the report")
            
            bot_message = await mod_channel.send("\n".join(report_data))
            self.under_review[bot_message.id] = complete_report

            

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        scores = self.eval_text(message.content)
        await mod_channel.send(self.code_format(scores))

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
    
        # Get the guild, channel, and message from the payload
        guild = self.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        if channel not in self.mod_channels.values():
            return
        message = await channel.fetch_message(payload.message_id)

        # Get the user who reacted
        # user = guild.get_member(payload.user_id)
        # print(user)
        user = payload.member
        print(user)

        # Print a test message to the console
        print(f'{user} reacted with {payload.emoji} to message: "{message.content}"')

        if message.id not in self.under_review:
            return
        
        # Get the report associated with this message
        report = self.under_review[message.id]

        # Check if the reaction is one of the valid reactions
        if payload.emoji.name not in self.reacts:
            return
        action = self.reacts[payload.emoji.name]
        print(f"Action: {action}")

        # Take action based on the reaction
        if action == 'ban':
            banned_user = report.message.author
            print(f"Banning user: {banned_user.name}")
            await message.channel.send(f'{banned_user.name} has been banned from group {self.group_num}.')
            self.under_review.pop(message.id) # Remove the report from under review
            # await banned_user.ban(reason="User has been banned by a moderator.")
            # await message.delete()
            # await report.message.delete()
        elif action == 'warn':
            warned_user = report.message.author
            print(f"Warning user: {warned_user.name}")
            await message.channel.send(f'{warned_user.name} has been sent a warning through direct message.')
            await warned_user.send(f'You have been warned for violating the rules in group {self.group_num}.')
            self.under_review.pop(message.id) # Remove the report from under review
            # await message.delete()
            # await report.message.delete()

        elif action == 'ignore':
            await message.channel.send(f'The report from {user.name} has been disregarded.')
            self.under_review.pop(message.id)


        
    
    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        return message

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "'"


client = ModBot()
client.run(discord_token)