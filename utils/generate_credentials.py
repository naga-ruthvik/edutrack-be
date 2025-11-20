import pandas as pd
import random
import os
import re
import string  # Required for random characters
from datetime import datetime

# --- Configuration ---
# This is the only place you need to make changes
CONFIG = {
    "input_file": "students.csv",
    "output_file": "student_credentials.csv",
    "roll_column": "Roll Number",
    "name_column": "Full Name",
    "dept_column": "Department",
    "COLLEGE_CODE": "88",  # Set your college code here
}
# --- End Configuration ---


def load_data(filepath):
    """Loads a CSV or Excel file into a pandas DataFrame."""
    print(f"Loading data from '{filepath}'...")
    _, ext = os.path.splitext(filepath)
    
    try:
        if ext == '.csv':
            return pd.read_csv(filepath)
        elif ext in ['.xls', '.xlsx']:
            return pd.read_excel(filepath)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    except FileNotFoundError:
        print(f"Error: Input file not found at '{filepath}'")
        return None
    except Exception as e:
        print(f"Error loading file: {e}")
        return None

from io import BytesIO
import os

def save_data(df, filename):
    """
    Converts the DataFrame into an in-memory file and returns it.
    Supports CSV and Excel formats.
    """
    _, ext = os.path.splitext(filename)
    output = BytesIO()

    try:
        if ext == ".csv":
            df.to_csv(output, index=False)
        elif ext in [".xls", ".xlsx"]:
            df.to_excel(output, index=False)
        else:
            raise ValueError(f"Unsupported output file format: {ext}")

        output.seek(0)  # reset pointer so Django can read it
        return output   # return file-like object

    except Exception as e:
        print(f"Error generating file: {e}")
        return None


def create_college_username(row, roll_col, dept_col, college_code):
    """
    Creates a unique username with the formula:
    (Year) + (College Code) + (Dept) + (Last 2 of Roll)
    Example: 2588CSE01
    """
    try:
        year_part = datetime.now().strftime('%y')
        college_part = str(college_code)
        
        dept_str = str(row[dept_col])
        dept_part = re.sub(r'[^a-zA-Z]', '', dept_str).upper()
        if not dept_part:
            dept_part = "XXX"

        roll_str = str(row[roll_col])
        roll_str_cleaned = re.sub(r'[^a-zA-Z0-9]', '', roll_str)
        
        if len(roll_str_cleaned) == 0:
            roll_part = "00"
        elif len(roll_str_cleaned) == 1:
            roll_part = roll_str_cleaned.zfill(2)
        else:
            roll_part = roll_str_cleaned[-2:]
        
        roll_part = roll_part.upper()
        base_user = year_part + college_part + dept_part + roll_part
        
        return base_user if base_user else f"user{row.name}"
        
    except Exception as e:
        print(f"Error on row {row.name}: {e}")
        return f"error{row.name}"

def create_custom_password(row, name_col):
    """
    Creates a secure password based on the new pattern:
    (3 lowercase) + (3 numbers) + _ + (First letter) + (Last letter)
    Example: nwg729_AX (for Alex) or vjx415_AH (for Alex Smith)
    """
    try:
        # 1. Random parts
        part1 = "".join(random.choices(string.ascii_lowercase, k=3))
        part2 = "".join(random.choices(string.digits, k=3))
        part3 = "_"
        
        # 2. Name part
        name_str = str(row[name_col]).strip()
        if not name_str:
            part4 = "XX" # Fallback
        else:
            first_letter = name_str[0]
            # Gets the last letter of the last name
            last_letter = name_str.split()[-1][-1] 
            part4 = (first_letter + last_letter).upper()
            
        return f"{part1}{part2}{part3}{part4}"
    
    except Exception:
        # Generic fallback in case of empty name or other error
        return f"err{random.randint(100,999)}_XX"


def deduplicate_usernames(username_series):
    """Handles duplicates efficiently."""
    final_usernames = []
    counts = {}
    
    for user in username_series:
        count = counts.get(user, 0)
        
        if count > 0:
            final_user = f"{user}{count + 1}"
        else:
            final_user = user
            
        final_usernames.append(final_user)
        counts[user] = count + 1
        
    return pd.Series(final_usernames, index=username_series.index)

def generate_usename_password(input_file, college_code):
    """Main function to run the credential generation process."""

    CONFIG = {
    "input_file": input_file,
    "output_file": "student_credentials.csv",
    "roll_column": "Roll Number",
    "name_column": "Full Name",
    "dept_column": "Department",
    "COLLEGE_CODE": college_code,  # Set your college code here
    }
    
    
    # 1. Load Data
    df = pd.read_csv(input_file)
    if df is None:
        return

    # 2. Validate Columns
    required_cols = [CONFIG["name_column"], CONFIG["roll_column"], CONFIG["dept_column"]]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"Error: Missing required columns: {missing_cols}")
        print(f"Available columns are: {list(df.columns)}")
        return

    # 3. Generate Usernames
    print("Generating college-format usernames...")
    base_usernames = df.apply(
        create_college_username,
        axis=1,
        args=(CONFIG["roll_column"], CONFIG["dept_column"], CONFIG["COLLEGE_CODE"])
    )

    # 4. Handle Duplicates
    print("Checking for duplicates...")
    df['Username'] = deduplicate_usernames(base_usernames)

    # 5. Generate Passwords
    print("Generating custom pattern passwords...")
    # This now uses df.apply() because it needs the 'name_column'
    df['Password'] = df.apply(
        create_custom_password,
        axis=1,
        args=(CONFIG["name_column"],)
    )

    # 6. Save Data
    file_obj=save_data(df, CONFIG["output_file"])
    return df,file_obj
