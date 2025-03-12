#!/usr/bin/env python3
import re
import sys
import os
import json

def process_file(input_path, output_path):
    """
    Process an asciinema cast v2 file to filter out certain sections based on ANSI cursor commands.
    
    Format: First line is a JSON header. Subsequent lines are JSON arrays: [timestamp, "o", "text"]
    
    If a text field contains "\u001b[ROW;COL]H" followed by "Atuin", skip it and all subsequent
    records until finding a text with "\u001b[ROW;(COL-1)H".
    
    Maintains consistent timestamps by not advancing time during skip sections.
    """
    skip_mode = False
    target_pattern = None
    ansi_pattern = re.compile(r'\u001b\[(\d+);(\d+)H')
    is_first_line = True
    last_timestamp = 0.0
    time_offset = 0.0  # Accumulator for time to subtract

    with open(input_path, 'r', encoding='utf-8') as infile, open(output_path, 'w', encoding='utf-8') as outfile:
        for line in infile:
            # Always include the header (first line)
            if is_first_line:
                outfile.write(line)
                is_first_line = False
                continue
            
            # Parse the JSON record
            try:
                record = json.loads(line)
                if not isinstance(record, list) or len(record) != 3 or record[1] != "o":
                    # If not a valid record, just write it out
                    outfile.write(line)
                    continue
                
                current_timestamp = float(record[0])
                text = record[2]  # The text content
                
                # If we're not in skip mode, check if we need to enter it
                if not skip_mode:
                    if '\u001b[' in text and 'Atuin' in text:
                        match = ansi_pattern.search(text)
                        if match:
                            row = match.group(1)
                            col = int(match.group(2))
                            # Create pattern for the ending sequence
                            target_pattern = f'\u001b[{row};{col-1}H'
                            skip_mode = True
                            # Start tracking time to subtract
                            skip_start_time = current_timestamp
                            continue  # Skip this record
                    
                    # If we're not skipping, write the record with adjusted timestamp
                    adjusted_timestamp = max(current_timestamp - time_offset, last_timestamp)
                    last_timestamp = adjusted_timestamp
                    record[0] = adjusted_timestamp
                    outfile.write(json.dumps(record) + '\n')
                    
                # If we're in skip mode, check if we should exit it
                else:
                    if target_pattern in text:
                        skip_mode = False
                        # Calculate how much time to subtract from future timestamps
                        time_offset += (current_timestamp - skip_start_time)
                        
                        # Write this record with adjusted timestamp
                        adjusted_timestamp = max(current_timestamp - time_offset, last_timestamp)
                        last_timestamp = adjusted_timestamp
                        record[0] = adjusted_timestamp
                        outfile.write(json.dumps(record) + '\n')
                    # Otherwise we're still in skip mode, don't write anything
            
            except json.JSONDecodeError:
                # If we can't parse the line as JSON, include it anyway
                outfile.write(line)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {os.path.basename(sys.argv[0])} input_file output_file")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist")
        sys.exit(1)

    process_file(input_file, output_file)
    print(f"Processed {input_file} -> {output_file}")
