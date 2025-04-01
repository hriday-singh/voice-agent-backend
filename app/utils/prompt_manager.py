import os
from pathlib import Path
from datetime import datetime
import shutil

# Base directory for prompt files
PROMPTS_DIR = Path(__file__).parent / "prompts"

def ensure_prompts_directory():
    """Ensure the prompts directory exists"""
    if not PROMPTS_DIR.exists():
        os.makedirs(PROMPTS_DIR, exist_ok=True)

def save_prompt_file(agent_id: str, prompt_text: str) -> str:
    """
    Save a prompt file for an agent
    
    Args:
        agent_id: The ID of the agent
        prompt_text: The prompt text to save
        
    Returns:
        str: The path to the saved prompt file
    """
    # Ensure the prompts directory exists
    ensure_prompts_directory()
    
    # Create the prompt file path
    prompt_file_path = PROMPTS_DIR / f"{agent_id}_prompt.txt"
    
    # Make sure we have a clean string
    cleaned_prompt = prompt_text.strip()
    
    # Save the prompt file, creating a backup if it already exists
    if prompt_file_path.exists():
        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = PROMPTS_DIR / f"{agent_id}_prompt_{timestamp}.bak"
        shutil.copy2(prompt_file_path, backup_path)
    
    # Write the new prompt
    with open(prompt_file_path, "w", encoding="utf-8") as f:
        f.write(cleaned_prompt)
    
    # Return the relative path from the root directory
    return str(prompt_file_path)

def get_prompt_content(agent_id: str) -> str:
    """
    Get the content of a prompt file
    
    Args:
        agent_id: The ID of the agent
        
    Returns:
        str: The content of the prompt file, or empty string if not found
    """
    prompt_file_path = PROMPTS_DIR / f"{agent_id}_prompt.txt"
    
    if not prompt_file_path.exists():
        return ""
    
    with open(prompt_file_path, "r", encoding="utf-8") as f:
        return f.read()

def list_prompt_files():
    """
    List all prompt files
    
    Returns:
        list: A list of prompt file names
    """
    ensure_prompts_directory()
    
    return [f.name for f in PROMPTS_DIR.glob("*_prompt.txt")] 