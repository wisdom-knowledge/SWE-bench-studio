import argparse
import json
import os

def split_instances(source_file, output_dir):
    """
    Splits a .jsonl file containing multiple task instances into individual .jsonl files in an output directory.

    Args:
        source_file (str): Path to the source .jsonl file.
        output_dir (str): Path to the directory where individual instance files will be saved.
    """
    if not os.path.exists(source_file):
        print(f"Error: Source file not found at {source_file}")
        return

    os.makedirs(output_dir, exist_ok=True)
    
    with open(source_file, 'r') as f_in:
        for i, line in enumerate(f_in):
            try:
                instance = json.loads(line)
                instance_id = instance.get("instance_id")
                if not instance_id:
                    print(f"Warning: Skipping line {i+1} as it does not have an 'instance_id'.")
                    continue
                
                # Sanitize instance_id to be a valid filename
                safe_filename = instance_id.replace('/', '_').replace(':', '_')
                target_file = os.path.join(output_dir, f"{safe_filename}.jsonl")
                
                with open(target_file, 'w') as f_out:
                    f_out.write(json.dumps(instance))
                
                print(f"Successfully created {target_file}")

            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from line {i+1}: {line.strip()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split a .jsonl file with multiple task instances into individual files.")
    parser.add_argument(
        "--source_file",
        type=str,
        required=True,
        help="Path to the source .jsonl file (e.g., gorm-task-instances.jsonl)."
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="Path to the directory to save the individual instance files."
    )
    args = parser.parse_args()
    split_instances(args.source_file, args.output_dir)
