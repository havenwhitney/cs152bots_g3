# google_genai.py
import os
import csv
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


def evaluate_msg_promptbased_gemini(message: str) -> str:
  """
  Uses a prompt-based approach to evaluate a message against a policy
  This is similar to the OpenAI example but uses Gemini's capabilities
  """
  with open("../assets/policy.txt") as file:
    policy = file.read()

  instructions = (
      "Answer with only a single character: 0 or 1 and a float from 0.0 to 1.0. Make sure there is a space between the int and float in the output"
      "Make sure your response is limited to only one of those two integers.\n"
      "Below is given a policy that describes what type of language counts as harassment or hate speech on our platform.\n"
      "If the user inputted message violates the criteria of the policy, respond with 1, otherwise, respond with 0.\n"
      "Then, give a confidence score for this classification. The closer to 1.0, the higher the confidence.\n\n"
      f"{policy}\n\n"
      f"User message: {message}"
  )

  response = client.models.generate_content(
      model="gemini-1.5-flash",
      contents=instructions
  )

  return response.text.strip()


def run_evaluation_gemini(file: str) -> str:
  """
  Runs the evaluation of a dataset against the Gemini model
  """

  # NOTE: Filename we want to use is anti-lgbt-cyberbullying.csv OR anti-lgbt-cyberbullying_small.csv
  # Format is message_id,message,ground_truth_label

  prefix = "../assets/"
  # join the prefix with the file name
  path = os.path.join(prefix, file)
  # with open(path, "r", encoding='utf8') as f:
  #   messages = f.readlines()

  # # remove ground truth labels
  # messages = [line.strip().split(",") for line in messages[1:]]

  with open(path, "r", encoding='utf8') as f:
    reader = csv.reader(f)
    next(reader)  # Skip the header row
    messages = [row for row in reader]

  print(f"Loaded {len(messages)} messages from {file}")
  print("First 5 messages:", messages[:5])
  to_eval = [(msg[0], msg[1]) for msg in messages if len(msg) >= 2]
 
  # go through and evaluate each message
  eval_results = []
  for message_id, message in to_eval:
    response = evaluate_msg_promptbased_gemini(message).strip()
    classification = int(response[:1])
    confidence = float(response[2:])
    eval_results.append((message_id, classification, float(confidence)))

  print(f"Evaluated {len(eval_results)} messages.")
  print("First 5 evaluation results:", eval_results[:5])
 
  # compare to ground truth labels
  accuracy_results = []
  true_pos = 0
  true_neg = 0
  false_pos = 0
  false_neg = 0
  for i in range(len(messages)):
    message_id, message, ground_truth = messages[i][0], messages[i][1], messages[i][2]
    classification, confidence = eval_results[i][1], eval_results[i][2]
    ground_truth_label = int(ground_truth)

    # calculate accuracy
    if classification == ground_truth_label:
      if classification == 1:
        true_pos += 1
      else:
        true_neg += 1
    else:
      if classification == 1:
        false_pos += 1
      else:
        false_neg += 1
    
    # add to results
    accuracy_results.append((message_id, classification, ground_truth_label, confidence))

  # save results to a file
  print("\nACCURACY RESULTS:")
  print("message_id,classification,ground_truth_label,confidence")
  print(accuracy_results)

  with open("evaluation_results.csv", "w") as f:
    f.write(f"Evaluation results for {file}\n")
    f.write("message_id,classification,ground_truth_label,confidence\n")
    for result in accuracy_results:
      f.write(f"{result[0]},{result[1]},{result[2]},{result[3]}\n")

    # return the aggregated stats of confusion matrix, recall, precision
    recall = true_pos / (true_pos + false_neg) if (true_pos + false_neg) > 0 else 0
    precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) > 0 else 0
    accuracy = (true_pos + true_neg) / len(messages) if len(messages) > 0 else 0
    confusion_matrix = {
        "true_positive": true_pos,
        "true_negative": true_neg,
        "false_positive": false_pos,
        "false_negative": false_neg,
    }
    print(f"Confusion Matrix: {confusion_matrix}")
    print(f"Recall: {recall:.2f}, Precision: {precision:.2f}, Accuracy: {accuracy:.2f}")

    # Add results to file
    f.write(f"Total messages: {len(messages)}\n")
    f.write(f"Confusion Matrix: {confusion_matrix}\n")
    f.write(f"Recall: {recall:.2f}, Precision: {precision:.2f}, Accuracy: {accuracy:.2f}\n")
  
  # Create msg to return
  msg = f"Running evaluation on Gemini for file {file}:\n"
  msg += f"Confusion Matrix: {confusion_matrix}\n"
  msg += f"Recall: {recall:.2f}, Precision: {precision:.2f}, Accuracy: {accuracy:.2f}\n"
  return msg


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