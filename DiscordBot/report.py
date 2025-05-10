from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    # MESSAGE_IDENTIFIED = auto()
    AWAITING_REASON = auto()
    AWAITING_CATEGORY = auto()
    AWAITING_DETAILS = auto()
    AWAITING_BLOCK = auto()
    REPORT_COMPLETE = auto()

# Map of report reasons (Spam, harassment, hate speech, or security concern) to the categories for each
report_reasons = {
    "spam": ["Unsolicited commercial content", "Bot generated or automated spam", "Scam or fraud links", "Other"],
    "hate speech": ["Racist or ethnic slurs",  "Homophobic or transphobic language", "Religious hate", "Gender-based hate or misogyny", "Nationality or immigration hate", "Ableist language", "Other"],
    "harassment": ["Bullying or personal attacks", "Sexual harassment", "Stalking or doxxing", "Other"],
    "security concern": ["Threats of violence or physical harm", "Self-harm or suicide content", "Child exploitation", "Other"]
}


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.guild_id = -1
        self.reason = ""
        self.category = ""
        self.has_details = False
        self.should_block = False
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            self.guild_id = int(m.group(1))
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.AWAITING_REASON
            self.message = message
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "Please select a reason for reporting this message:", \
                        "`spam`, `hate speech`, `harassment`, or `security concern`"]
        
        if self.state == State.AWAITING_REASON:
            report_reason = message.content.lower()
            if report_reason not in report_reasons:
                return ["I'm sorry, I don't recognize that reason. Please choose one of the following:", \
                        "`spam`, `hate speech`, `harassment`, or `security concern`"]
            self.reason = report_reason
            self.state = State.AWAITING_CATEGORY
            self.categories = report_reasons[report_reason]

            reply = "You have selected" + f" `{self.reason}`.\n"

            reply += "Please select a category for your report:\n"
            for i, category in enumerate(self.categories):
                reply += f"`{i + 1}`: {category}\n"
            reply += "Please respond with the number of the category you want to choose."
            return [reply]
        
        
        if self.state == State.AWAITING_CATEGORY:
            try:
                category_index = int(message.content) - 1
                if category_index < 0 or category_index >= len(self.categories):
                    raise ValueError
            except ValueError:
                reply = "I'm sorry, I don't recognize that category. Please choose one of the following:\n"
                for i, category in enumerate(self.categories):
                    reply += f"`{i + 1}`: {category}\n"
                reply += "Please respond with the number of the category you want to choose."
                return [reply]
            
            self.category = report_reasons[self.reason][category_index]
            self.state = State.AWAITING_DETAILS

            reply = "You have selected" + f" `{self.reason}`: `{self.category}`.\n"
            reply += "Would you like to provide any additional details or screenshots to help us review this report? (`yes` or `no`)"

            return [reply]


        if self.state == State.AWAITING_DETAILS:
            user_msg = message.content.lower()
            if user_msg != "yes" and user_msg != "no":
                return ["I'm sorry, I don't recognize that response. Please respond with `yes` or `no`."]
            if user_msg == "yes":
                self.has_details = True
                self.state = State.AWAITING_BLOCK
                return ["Thank you! A human moderator will be reaching out to you shortly through direct message for additional details. \n", \
                "Would you like to block this user from contacting you further? (`yes` or `no`)"]
            else:
                self.state = State.AWAITING_BLOCK
                return ["Would you like to block this user from contacting you further? (`yes` or `no`)"]


        if self.state == State.AWAITING_BLOCK:
            user_msg = message.content.lower()
            if user_msg != "yes" and user_msg != "no":
                return ["I'm sorry, I don't recognize that response. Please respond with `yes` or `no`."]
            if user_msg == "yes":
                self.should_block = True
                self.state = State.REPORT_COMPLETE
                return ["Thanks for your report. This account will be blocked from contacting you further. \n", \
                    "Our moderation team will review the message and take necessary action, which may include warning, suspension, or account removal."]
            else:
                self.state = State.REPORT_COMPLETE
                return ["Thanks for your report. Our moderation team will review the message and take necessary action, which may include warning, suspension, or account removal."]

        if self.state == State.REPORT_COMPLETE:
            reply = "Your report has been submitted. Thank you for helping us keep our community safe!"

            return [reply]
    
            

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

