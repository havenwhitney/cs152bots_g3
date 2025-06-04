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
  Answer with only a single character: 0 or 1. Make sure your response is limited to only one of those two integers.
  Below is given a policy that describes what type of language counts as harassment or hate speech on our platform.
  If the user inputted message violates the criteria of the policy, respond with 1, otherwise, respond with 0\n
  """

  instructions += policy

  response = client.responses.create(
    model="gpt-4.1-mini",
    instructions=instructions,
    input=message
  )

  print(response.output_text)
  return 0

# Uses the default openai moderation endpoint to detect hate speech / harassment
def evaluate_msg_moderation_api_openai(message: str) -> int:
  response = client.moderations.create(
    model="text-moderation-latest",
    input=message
  )

  categories = response.results[0].categories
  category_scores = response.results[0].category_scores 

  print(f"harassment: {categories.harassment}, {category_scores.harassment}")
  print(f"harassment/threatening: {categories.harassment_threatening}, {category_scores.harassment_threatening}")
  print(f"hate: {categories.hate}, {category_scores.hate}")
  print(f"hate: {categories.hate_threatening}, {category_scores.hate_threatening}\n")

  return 0
