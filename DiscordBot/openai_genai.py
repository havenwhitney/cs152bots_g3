# google_genai.py
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Simple prompt based approach for detecting hate speech / harassment
# Uses policy as prompt engineered input for classifying a chat message
def evaluate_msg_promptbased_openai(message: str) -> int:
  with open("../assets/policy.txt") as file:
    policy = file.read()

  instructions = """
  Answer only in the following format int, float: 0 or 1 and a float from 0.0 to 1.0. Make sure your response is limited to only one of those two integers for
  the first value. Also make sure that there is a space between the int and float.
  Below is given a policy that describes what type of language counts as harassment or hate speech on our platform.
  If the user inputted message violates the criteria of the policy, respond with 1, otherwise, respond with 0
  Then, give a confidence score for this classification between 0.0 and 1.0. The closer to 1.0, the the higher you are confident in correctly
  classifying the message.\n
  """

  instructions += policy

  response = client.responses.create(
    model="gpt-4.1-mini",
    instructions=instructions,
    input=message
  )

  print(response.output_text.strip())
  return response.output_text.strip()

# Uses the default openai moderation endpoint to detect hate speech / harassment
def evaluate_msg_moderation_api_openai(message: str) -> dict:
  response = client.moderations.create(
    model="text-moderation-latest",
    input=message
  )

  categories = response.results[0].categories
  category_scores = response.results[0].category_scores 

  data = {
    "harrassment": (categories.harassment, category_scores.harassment),
    "harrassment_threatening": (categories.harassment_threatening, category_scores.harassment_threatening),
    "hate": (categories.hate, category_scores.hate),
    "hate_threatening": (categories.hate_threatening, category_scores.hate_threatening)
  }

  print(data)
  return data
