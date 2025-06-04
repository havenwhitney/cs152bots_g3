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

