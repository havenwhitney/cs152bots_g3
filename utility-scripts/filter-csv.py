# filter-csv

"""
The purpose of this script is to take in the default csv (anti-lgbt-cyberbullying.csv)
and output a filtered version of it only retaining rows with text containing <= 30 tokens.
This is in order to save money on training a GPT3.5 fine-tuned classifier.
As a tradeoff, this will reduce accuracy on classifying longer messages
"""

import pandas as pd
import tiktoken 

df = pd.read_csv("../assets/anti-lgbt-cyberbullying.csv")
enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

def is_less_than_30_tokens(text, max_tokens=30):
  return len(enc.encode(str(text))) <= max_tokens

filtered_df = df[df["text"].apply(is_less_than_30_tokens)]
filtered_df.to_csv("../assets/anti-lgbt-cyberbullying-filtered.csv")

print("original csv has this many rows: ", len(df))
print("filtered csv has this many rows: ", len(filtered_df))

# PRINT OUTPUT:
# original csv has this many rows:  4299
# filtered csv has this many rows:  2212
