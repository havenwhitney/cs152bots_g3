# csv-to-finetune-jsonl.py

"""
The purpose of this code is to wrangle an input csv with id,text, 0 or 1 into 
a format that can be inputted to chatgpt3.5 for fine-tuning 

The outputted file is used for training a classifier via model fine-tuning. 

NOTE: this approach failed accompanied by the following message from openai:
The job failed due to an invalid training file. This training file was blocked 
because too many examples were flagged by our moderation API for containing content 
that violates OpenAI's usage policies in the following categories: hate. Use the 
free OpenAI Moderation API to identify these examples and remove them from your 
training data. See https://platform.openai.com/docs/guides/moderation for more information.
"""

import pandas as pd
import json 

df = pd.read_csv("../assets/anti-lgbt-cyberbullying-filtered.csv")
output_file = "../assets/anti_lgbt_finetune.jsonl"

with open(output_file, "w", encoding="utf-8") as f:
  for index, row in df.iterrows():
    prompt = str(row["text"]).strip()
    # We need to cast to an int and back into a string in case of null values 
    # or pandas converting to float (1.0 or 0.0):
    label = str(int(row["anti_lgbt"]))

    json_line = {
      "messages": [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": label}
      ]
    }

    f.write(json.dumps(json_line) + "\n")

print(f"Created or Updated {output_file}")
