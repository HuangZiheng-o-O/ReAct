import os
import json
import pprint

# Specify the directory containing the JSON files
directory = '/Users/huangziheng/PycharmProjects/ReAct/prompts'

# Iterate over all files in the directory
for filename in os.listdir(directory):
    if filename.endswith('.json'):
        # Construct the full path to the file
        filepath = os.path.join(directory, filename)

        # Load the JSON data
        with open(filepath, 'r') as file:
            data = json.load(file)

        # Prepare the output file path (same name, but with .txt extension)
        output_filename = os.path.splitext(filename)[0] + '.txt'
        output_filepath = os.path.join(directory, output_filename)

        # Write the formatted JSON data to the output file
        with open(output_filepath, 'w') as output_file:
            pprint.pprint(data, output_file, indent=2)

print("All JSON files have been processed and saved as .txt files.")
