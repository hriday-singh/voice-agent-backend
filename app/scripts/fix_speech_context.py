#!/usr/bin/env python3
"""
Fix speech_context serialization in database

This script iterates through all agent configs in the database and ensures
that speech_context fields are properly serialized as JSON strings.
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.database.db import get_db
from app.models.models import AgentConfig
from sqlmodel import select, Session

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_speech_context_in_db():
    """
    Find all agent configs with speech_context values that are lists
    instead of JSON strings and convert them to properly serialized JSON.
    """
    with get_db() as session:
        # Get all agent configs
        agent_configs = session.exec(select(AgentConfig)).all()
        
        fixed_count = 0
        for agent_config in agent_configs:
            # Check if speech_context is a list (should be a JSON string)
            if isinstance(agent_config.speech_context, list):
                logger.info(f"Found list speech_context for agent {agent_config.agent_type}")
                
                try:
                    # Convert list to JSON string
                    json_str = json.dumps(agent_config.speech_context)
                    agent_config.speech_context = json_str
                    session.add(agent_config)
                    fixed_count += 1
                    logger.info(f"Fixed speech_context for agent {agent_config.agent_type}")
                except Exception as e:
                    logger.error(f"Error serializing speech_context for agent {agent_config.agent_type}: {e}")
        
        if fixed_count > 0:
            session.commit()
            logger.info(f"Fixed {fixed_count} agent configs with list speech_context")
        else:
            logger.info("No agent configs with list speech_context found")

def main():
    try:
        logger.info("Starting speech_context fix script")
        fix_speech_context_in_db()
        logger.info("Successfully completed speech_context fix script")
    except Exception as e:
        logger.error(f"Error running fix script: {e}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main()) 