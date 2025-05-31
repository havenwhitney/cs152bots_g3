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

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']
    os.environ["GEMINI_API_KEY"] = tokens["gemini"]

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./google-service-account.json"
# google imports must come after the above line
from google_genai import test_generate_gemini

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = 3
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.user_review = {} # Map from report message IDs to the report
        self.post_review = {}
        

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

    async def handle_user_review(self, message, report, payload, user):
        valid_reacts = { # valid reacts for the bot to respond to
            '🔨': 'ban',
            '⚠️': 'warn',
            '❌': 'ignore',
            '❓': 'unsure'
            }
        
        reacts_msg = "**What should be the next steps taken towards this post?** \n"
        reacts_msg += "Please react to this message with one of the following: \n"
        reacts_msg += "🗑️ to delete the message \n"
        reacts_msg += "‼️ to add a disclaimer \n"
        reacts_msg += "❌ to not take action \n"
       

        # Check if the reaction is one of the valid reactions
        if payload.emoji.name not in valid_reacts:
            return
        action = valid_reacts[payload.emoji.name]
        print(f"Action: {action}")

        # Take action based on the reaction
        if action == 'ban':
            banned_user = report.message.author
            print(f"Banning user: {banned_user.name}")
            await message.channel.send(f'{banned_user.name} has been banned from group {self.group_num}.')
            bot_msg = await message.channel.send(reacts_msg)
            self.post_review[bot_msg.id] = self.user_review.pop(message.id) 
            await report.message.channel.send(f"User {banned_user.name} has been banned by a moderator for {report.reason}.")
        elif action == 'warn':
            warned_user = report.message.author
            print(f"Warning user: {warned_user.name}")
            await message.channel.send(f'{warned_user.name} has been sent a warning through direct message.')
            warning = f"**Warning:** A message you have sent in group {self.group_num} has been flagged for review by a moderator. \n"
            warning += f"This post may contain language that is considered {report.reason}. \n"
            warning += "Please be mindful of the language you use in this group. \n"
            warning += "If you have any questions, please reach out to a moderator."
            await warned_user.send(warning)

            bot_msg = await message.channel.send(reacts_msg)
            self.post_review[bot_msg.id] = self.user_review.pop(message.id) # Remove the report from under review

        elif action == 'ignore':
            await message.channel.send(f'The report from {user.name} has been disregarded.')
            await message.channel.send(f'**This report is finished.**')
            self.user_review.pop(message.id)
        
        elif action == 'unsure':
            await message.channel.send(f'If the user has been flagged in the past, please forward this report to an advanced moderator for further review.')
            await message.channel.send(f'This user will be flagged in the system and warned in case of future reports.')
            
            warned_user = report.message.author
            warning = f"**Warning:** A message you have sent in group {self.group_num} has been flagged for review by a moderator. \n"
            warning += f"This post may contain language that is considered {report.reason}. \n"
            warning += "Please be mindful of the language you use in this group. \n"
            warning += "If you have any questions, please reach out to a moderator."
            await warned_user.send(warning)
            bot_msg = await message.channel.send(reacts_msg)
            self.post_review[bot_msg.id] = self.user_review.pop(message.id)

    
    async def handle_post_review(self, message, report, payload, user):
         # delete message, add disclaimer, ignore
        valid_reacts = {
            '🗑️': 'delete',
            '‼️': 'disclaimer',
            '❌': 'ignore',
        }

        # Check if the reaction is one of the valid reactions
        if payload.emoji.name not in valid_reacts:
            return
        action = valid_reacts[payload.emoji.name]
        print(f"Action: {action}")

        if action == 'delete':
            message_author = report.message.author
            await message.channel.send(f'The reported message from {message_author} has been deleted.')
            await report.message.delete() # CHECK IN A BIT
            self.post_review.pop(message.id)
        elif action == 'disclaimer':
            message_author = report.message.author
            await message.channel.send(f'The reported message from {message_author} has received a disclaimer.')
            # SEND DISCLAIMER MESSAGE IN REPLY ON CHANNEL OF REPORTED MESSAGE
            disclaimer_msg = "**Disclaimer:** This message has been flagged for review by a moderator. \n"
            disclaimer_msg += f"This post may contain language that is considered {report.reason}. \n"
            await report.message.reply(disclaimer_msg)
        
            self.post_review.pop(message.id)
        elif action == 'ignore':
            await message.channel.send(f'No further action will be taken on the reported message.')
            # await message.channel.send(f'Moderation flow complete.')
            self.post_review.pop(message.id)
        
        await message.channel.send(f'**This report is finished.**')

    
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
            report_data.append(f"_Report from {message.author.name} ({message.author.id})_")
            report_data.append(f"**Message:** \n```{reported_msg.content}\n```")
            report_data.append(f"**Reason**: {complete_report.reason}")
            report_data.append(f"**Category**: {complete_report.category}")
            if complete_report.has_details:
                report_data.append("📝 **User would like to provide more details to a moderator.**")
            if complete_report.should_block:
                report_data.append("🚫 **User has requested to block this user from contacting them further.**")
            report_data.append("Report complete. \n")
            report_data.append("If you would like to see the message in context, click on the link below:")
            report_data.append(f"https://discord.com/channels/{complete_report.guild_id}/{reported_msg.channel.id}/{reported_msg.id}\n")
            report_data.append("**To take action**, react to this message with one of the following:")
            report_data.append("🔨 to ban the user")
            report_data.append("⚠️ to warn the user")
            report_data.append("❌ to ignore the report")
            report_data.append("❓ if you are unsure of what to do")
            
            bot_message = await mod_channel.send("\n".join(report_data))
            self.user_review[bot_message.id] = complete_report

            

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

        if message.id not in self.user_review and message.id not in self.post_review:
            return
        
       

        if message.id in self.user_review:
             # Get the report associated with this message
            report = self.user_review[message.id]

            await self.handle_user_review(message, report, payload, user)

            

        else:
            # Get the report associated with this message
            report = self.post_review[message.id]

            await self.handle_post_review(message, report, payload, user)

           

        
    
    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''

        # If a message starts with "prompt: ", generate response from genai
        if (message.startswith("prompt: ")):
            return test_generate_gemini(message[8:])
        
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