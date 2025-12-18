# Fight.ID Add CSV Email Script
# 将邮箱信息合并到 tokens CSV

import pandas as pd

file_csv = 'tokens_email.csv'
file_txt = 'email.txt'
output_file = 'tokens_email_info.csv'

# 1. Read email.txt and extract emails
emails = []
try:
    with open(file_txt, 'r', encoding='utf-8') as f:
        # Extract the part before the first '----'
        emails = [line.split('----')[0].strip() for line in f if line.strip()]
except FileNotFoundError:
    print(f"Error: '{file_txt}' not found. Cannot merge data.")
    exit()
except Exception as e:
    print(f"Error reading '{file_txt}': {e}")
    exit()

# 2. Read tokens_email.csv
df = None
try:
    df = pd.read_csv(file_csv, sep=',')
except Exception as e:
    print(f"Error loading '{file_csv}': {e}")
    exit()

# 3. Add the 'email' column
if len(emails) != len(df):
    print(f"Warning: Email count ({len(emails)}) does not match CSV data row count ({len(df)}). Adjusting.")
    if len(emails) > len(df):
        emails = emails[:len(df)]
    elif len(emails) < len(df):
        emails.extend(['MISSING_EMAIL'] * (len(df) - len(emails)))

# 插入 'email' 列到 'token' 之后
df.insert(2, 'email', emails)

# 4. Save to the new CSV file
df.to_csv(output_file, index=False, encoding='utf-8')

print(f"Data successfully merged and saved to '{output_file}'.")

