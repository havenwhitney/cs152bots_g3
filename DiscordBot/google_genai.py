# google_genai.py
import os
from google import genai
from google.genai import types
import base64 # need this if we wanna send images and not just text

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def test_generate_gemini(prompt: str) -> str:
  """
  Uses a simple api key to access gemini models
  if we can switch to vertex (part of google genai suite), 
  it will afford more customizing of generation params (see below)
  """

  response = client.models.generate_content(
      model="gemini-1.5-flash",
      contents=prompt
  )

  return response.text.strip()


# This is a simple test function that takes a single string prompt using vertex ai (currently not working)
def test_generate_vertex(prompt: str):
    client = genai.Client(
        vertexai=True,
        project="cs-152-discordbot",
        location="us-central1",
    )

    contents = [
        types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )
    ]

    config = types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=256,
    )

    print(f"Inputted Prompt: {prompt}")
    print(f"Output from Gemini:")
    for chunk in client.models.generate_content_stream(
        model="gemini-1.5-flash",
        contents=contents,
        config=config,
    ):
        print(chunk.text, end="")


# This is the default example for generation from the google api documentation for vertex ai (more complicated setup)
# NOTE: we need to set the "parts" variable as our prompt - this can be text, images, etc.
def generate():
  client = genai.Client(
      vertexai=True,
      project="cs-152-discordbot",
      location="global",
  )


  model = "gemini-2.5-flash-preview-05-20"
  contents = [
    types.Content(
      role="user",
      parts=[
      ]
    )
  ]

  # the params that are set here will be important if we want to use or 
  # test against google genai's default safety settings
  generate_content_config = types.GenerateContentConfig(
    temperature = 1,
    top_p = 1,
    seed = 0,
    max_output_tokens = 65535,
    safety_settings = [types.SafetySetting(
      category="HARM_CATEGORY_HATE_SPEECH",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_HARASSMENT",
      threshold="OFF"
    )],
  )

  for chunk in client.models.generate_content_stream(
    model = model,
    contents = contents,
    config = generate_content_config,
    ):
    print(chunk.text, end="")