import shutil
import os

# Get the current directory
current_directory = os.getcwd()

# Loop through all files in the current directory
for item in os.listdir(current_directory):
    if item.endswith('.py'):
        continue

    for item2 in os.listdir(item):
        if item2.endswith('.zip'):
            # Find the last underscore in the filename
            last_underscore_index = item2.rfind('_')
            
            if last_underscore_index != -1:
                # Extract the part of the filename after the last underscore
                item2_short = item2[last_underscore_index + 1:]
        
                old_file_name = os.path.join(current_directory, item, item2)
                file_name = os.path.join(current_directory, item2_short)
                print(f"Copying {old_file_name} to {file_name}...")
                
                shutil.copyfile(old_file_name, file_name)
            
            

print("All files copied and renamed.")