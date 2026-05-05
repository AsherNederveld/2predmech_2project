#!/bin/bash

# Ensure temp.txt and multicore.sub exist
if [[ ! -f temp.txt ]] || [[ ! -f multicore.sub ]]; then
    echo "Error: temp.txt or multicore.sub not found in the current directory."
    exit 1
fi

# Read through temp.txt
while IFS= read -r line || [[ -n "$line" ]]; do
    # Trim leading whitespace
    trimmed_line="${line#"${line%%[![:space:]]*}"}"
    
    # Skip empty lines and lines starting with '#'
    if [[ -z "$trimmed_line" ]] || [[ "$trimmed_line" == \#* ]]; then
        continue
    fi

    echo "Preparing submission for: $trimmed_line"
    
    # Replace the my_exe definition in multicore.sub
    # This uses sed to find the line starting with 'my_exe' and replaces the whole line
    sed -i "s/^my_exe[[:space:]]*=.*/my_exe                = $trimmed_line/" multicore.sub
    
    # Submit the job to HTCondor
    condor_submit multicore.sub
    
done < temp.txt

echo "All jobs submitted!"
